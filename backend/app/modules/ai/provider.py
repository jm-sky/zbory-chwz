"""OpenRouter provider for structured AI extraction.

Uses the OpenAI SDK's `response_format: json_schema` (strict mode) instead of
regex-parsing a fenced JSON block out of a free-form chat reply — the latter
is the pattern used by the sibling gear-stack app's AI module and is fragile.
"""

import json
import logging

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.modules.ai.schemas import ExtractionResult, VerificationResult

logger = logging.getLogger(__name__)

_VERIFICATION_SYSTEM_PROMPT = (
    "Oceniasz wiarygodność aktualizacji danych zboru przesłanej e-mailem od duchownego "
    "(pastora, biskupa lub diakona). Dla ochrony prywatności NIE dostajesz imienia nadawcy "
    "ani poprzednich wartości pól — zamiast tego dostajesz: rolę rozpoznanego nadawcy i zbór, "
    "do którego ma dostęp; lokalny sygnał, czy podpis/treść maila wygląda na zgodny ze znanym "
    "nadawcą (obliczony poza tym promptem); listę proponowanych zmian pól z nową wartością, "
    "informacją czy pole miało wcześniej jakąkolwiek wartość (bez podawania jaką) oraz lokalnym "
    "sygnałem, czy nowa wartość ma poprawny format; a także oryginalną treść maila. Oceń w skali "
    "0-1 (trust_score), jak bardzo ta zmiana jest spójna i wiarygodna: czy lokalny sygnał podpisu "
    "jest pozytywny, czy zmiany są sensowne (nie wyglądają na spam, żart, pomyłkę czy próbę "
    "wprowadzenia fałszywych danych — zwróć szczególną uwagę na pola oznaczone jako mające "
    "wątpliwy format), i czy treść maila faktycznie uzasadnia każdą z wyekstrahowanych zmian. "
    "Treść maila niezwiązana z podanymi zmianami, sprzeczności, brak podpisu pasującego do "
    "znanego nadawcy, albo brak jasnego uzasadnienia zmiany powinny obniżać trust_score. Zwróć "
    "trust_score oraz krótkie uzasadnienie po polsku."
)

_VERIFICATION_JSON_SCHEMA = {
    "name": "verification_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "trust_score": {"type": "number"},
            "reasoning": {"type": "string"},
        },
        "required": ["trust_score", "reasoning"],
        "additionalProperties": False,
    },
}

_EXTRACTION_SYSTEM_PROMPT = (
    "Wyciągnij z poniższej notatki dane o zborach (kongregacjach) w niej wspomnianych. "
    "Dla każdego zboru zwróć jego nazwę, adres (ulica, miasto, kod pocztowy, województwo "
    "jako ASCII slug np. 'lubuskie', kraj jako kod ISO 3166-1 alpha-2, domyślnie 'PL'), "
    "oficjalną stronę WWW zboru, oficjalny e-mail zboru (nie osoby prywatnej), numer konta "
    "bankowego zboru (IBAN lub polski NRB) oraz dane osoby kontaktowej (imię i nazwisko, "
    "tytuł/funkcja np. 'Pastor', telefon, e-mail), jeśli są podane. Dla pól, których nie ma "
    "w tekście, zwróć null — nie zgaduj brakujących danych."
)

_CONGREGATION_FIELDS = (
    "name",
    "street",
    "city",
    "postal_code",
    "province",
    "country",
    "website",
    "email",
    "iban",
    "contact_name",
    "contact_title",
    "contact_phone",
    "contact_email",
)

# Hand-written (not generated from the Pydantic model) so it satisfies
# OpenAI/OpenRouter strict-mode structured outputs: every property listed in
# "required", nullability expressed via a ["string", "null"] type union, and
# "additionalProperties": False at every object level.
_EXTRACTION_JSON_SCHEMA = {
    "name": "extraction_result",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "congregations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        **{field: {"type": ["string", "null"]} for field in _CONGREGATION_FIELDS if field != "name"},
                    },
                    "required": list(_CONGREGATION_FIELDS),
                    "additionalProperties": False,
                },
            },
        },
        "required": ["congregations"],
        "additionalProperties": False,
    },
}


class OpenRouterProvider:
    """Thin wrapper around the OpenAI SDK pointed at OpenRouter."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        settings = get_settings()
        self._model = model or settings.ai.model
        self._client = AsyncOpenAI(
            api_key=api_key or settings.ai.openrouter_api_key,
            base_url=base_url or settings.ai.openrouter_base_url,
        )

    async def extract_congregations(self, raw_text: str, *, context_hint: str | None = None) -> ExtractionResult:
        """Extract structured congregation data from free-text notes.

        `context_hint` is prepended to the user message (not the system
        prompt, so the base extraction behaviour stays unchanged for the
        pasted-text import flow). Used by the clergy e-mail import to supply
        the sender's own congregation name when the e-mail body itself never
        states it — `name` is a required field in the schema below, so
        without a hint an e-mail like "zmieńcie mój numer telefonu na..."
        would extract nothing at all.
        """
        user_content = raw_text if not context_hint else f"{context_hint}\n\n---\n\n{raw_text}"
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": _EXTRACTION_JSON_SCHEMA,
            },
            temperature=0,
        )  # type: ignore[call-overload]
        content = response.choices[0].message.content
        if not content:
            logger.warning("AI extraction returned an empty response")
            return ExtractionResult()
        return ExtractionResult.model_validate(json.loads(content))

    async def verify_extraction(self, raw_text: str, sender_context: str, diff_summary: str) -> VerificationResult:
        """Second-pass trust assessment for a clergy e-mail update (see VerificationResult).

        Deliberately a separate call from extract_congregations rather than
        one combined prompt: this one gets the sender's role/church and the
        field diff as additional context the extraction call never sees, and
        a low-trust result here must never silently affect the extracted
        values themselves.

        `sender_context`/`diff_summary` are built by
        email_import_service._resolve_and_maybe_apply to deliberately exclude
        the sender's name and the fields' previous values — see the comments
        there for why (both are PII pulled from the database rather than
        already present in `raw_text`, unlike everything else this call
        sends).
        """
        user_content = f"Kontekst nadawcy: {sender_context}\n\nProponowane zmiany:\n{diff_summary}\n\nOryginalna treść maila:\n---\n{raw_text}\n---"
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": _VERIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": _VERIFICATION_JSON_SCHEMA,
            },
            temperature=0,
        )  # type: ignore[call-overload]
        content = response.choices[0].message.content
        if not content:
            logger.warning("AI verification returned an empty response")
            return VerificationResult(
                trust_score=0.0,
                reasoning="Pusta odpowiedź modelu AI — wymagana ręczna weryfikacja.",
            )
        return VerificationResult.model_validate(json.loads(content))
