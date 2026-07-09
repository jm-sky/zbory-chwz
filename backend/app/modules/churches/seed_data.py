"""Seed constants for church hierarchy."""

CHWZ_COMMUNITY_SLUG = "chwz"
CHWZ_ORG_TENANT_NAME = "CHWZ"

REGIONS_SEED = [
    {"slug": "dolny-slask", "name": "Dolny Śląsk"},
    {"slug": "gorny-slask", "name": "Górny Śląsk"},
    {"slug": "polnocno-wschodni", "name": "Północno-Wschodni"},
    {"slug": "centralny", "name": "Centralny"},
]

CITY_REGION_MAP: dict[str, str] = {
    "warszawa": "centralny",
    "lodz": "centralny",
    "łódź": "centralny",
    "gdansk": "polnocno-wschodni",
    "gdańsk": "polnocno-wschodni",
    "goldap": "polnocno-wschodni",
    "gołdap": "polnocno-wschodni",
    "bydgoszcz": "polnocno-wschodni",
    "ketrzyn": "polnocno-wschodni",
    "kętrzyn": "polnocno-wschodni",
    "bialystok": "polnocno-wschodni",
    "białystok": "polnocno-wschodni",
    "zabrze": "gorny-slask",
}

CITY_ALIASES_SEED = [
    {"country_slug": "polska", "alias_slug": "warszawa", "city_slug": "warszawa"},
    {"country_slug": "polska", "alias_slug": "lodz", "city_slug": "lodz"},
    {"country_slug": "polska", "alias_slug": "krakow", "city_slug": "krakow"},
    {"country_slug": "polska", "alias_slug": "gdansk", "city_slug": "gdansk"},
]

SERVICE_TYPES_SEED = [
    ("biskup_naczelny", "Biskup naczelny", "community", "bishop", False, 10),
    ("biskup_senior", "Biskup senior", "community", "bishop", True, 20),
    ("biskup_regionu", "Biskup regionu", "region", "regional_bishop", False, 30),
    ("biskup", "Biskup", "community", "bishop", False, 40),
    ("pastor", "Pastor", "church", "pastor", False, 50),
    ("mlodszy_pastor", "Młodszy pastor", "church", "pastor", False, 60),
    ("senior_pastor", "Senior pastor", "church", "pastor", True, 70),
    ("diakon", "Diakon", "church", "diacon", False, 80),
    ("senior_diakon", "Senior diakon", "church", "diacon", True, 90),
    ("lider_mlodziezowy", "Lider młodzieżowy", "church", None, False, 100),
]

PASTOR_SERVICE_SLUGS = frozenset({"pastor", "mlodszy_pastor", "senior_pastor"})

TITLE_TO_SERVICE_SLUG: dict[str, str] = {
    "pastor": "pastor",
    "diakon": "diakon",
    "diacon": "diakon",
}
