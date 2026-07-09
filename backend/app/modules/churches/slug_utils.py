"""Slug normalization for church URLs."""

import re
import unicodedata

_POLISH_MAP = str.maketrans(
    {
        "ą": "a",
        "ć": "c",
        "ę": "e",
        "ł": "l",
        "ń": "n",
        "ó": "o",
        "ś": "s",
        "ź": "z",
        "ż": "z",
        "Ą": "a",
        "Ć": "c",
        "Ę": "e",
        "Ł": "l",
        "Ń": "n",
        "Ó": "o",
        "Ś": "s",
        "Ź": "z",
        "Ż": "z",
    }
)

_COUNTRY_SLUGS = {
    "poland": "polska",
    "polska": "polska",
}


def slugify(value: str) -> str:
    if not value:
        return ""
    text = value.strip().translate(_POLISH_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def country_slug(country: str) -> str:
    base = slugify(country)
    return _COUNTRY_SLUGS.get(base, base or "polska")


def city_slug(city: str) -> str:
    return slugify(city)


def church_slug(name: str) -> str:
    return slugify(name)
