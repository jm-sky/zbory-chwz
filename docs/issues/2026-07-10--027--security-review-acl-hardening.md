# Issue 027 — Review platformy kościelnej (dokument)

**Data:** 2026-07-10  
**Status:** `done` (2026-07-10)  
**Commit:** `c90702f`  
**Review:** [2026-07-10--church-platform-review.md](../reviews/2026-07-10--church-platform-review.md)  
**Z tego samego promptu:** [#030](./2026-07-10--030--acl-endpoint-enforcement.md), [#031](./2026-07-10--031--tenant-soft-delete-church-provisioning.md), [#016](./2026-07-10--016--congregation-write-endpoint-for-non-admins.md), [#017](./2026-07-10--017--authorization-hardening-followups.md)

## Prompt (Claude Code)

> Wczytaj dokumentacje,aby rozumiec kontekst.  
> Zrob review projektu - zgodnosc z planem + sugestie dodatkowe, security, jakosc kodu, UX.  
> Zapisz wyniki w docs/reviews/  
> Potem popraw oczywiste rzeczy, commit push. Reszte omowimy.

*(sesja `1e556b31`)*

## Decyzja

Review jako **osobny artefakt** — lista bugów (BUG-1…), luk ACL i UX bez mieszania z kodem napraw. „Oczywiste” poprawki poszły w osobnych commitach → issue [#030](./2026-07-10--030--acl-endpoint-enforcement.md), [#031](./2026-07-10--031--tenant-soft-delete-church-provisioning.md). Reszta → [#016](./2026-07-10--016--congregation-write-endpoint-for-non-admins.md), [#017](./2026-07-10--017--authorization-hardening-followups.md).

## Implementacja

- `c90702f` — `docs: church platform review + follow-up issues 016, 017`

## Weryfikacja

- Plik review w `docs/reviews/` z datą 2026-07-10
- Każdy BUG z review ma issue lub jest oznaczony jako done
