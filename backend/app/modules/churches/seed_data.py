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
    ("biskup_regionu", "Biskup regionalny", "region", "regional_bishop", False, 20),
    ("biskup", "Biskup", "community", "bishop", False, 30),
    ("biskup_senior", "Biskup senior", "community", "bishop", True, 40),
    ("pastor", "Pastor", "church", "pastor", False, 50),
    ("senior_pastor", "Pastor senior", "church", "pastor", True, 60),
    ("diakon", "Diakon", "church", "diacon", False, 70),
    ("diakon_skarbnik", "Diakon - Skarbnik", "church", "diacon", False, 80),
    ("czlonek_rady", "Członek Rady", "church", None, False, 90),
    ("lider_mlodziezowy", "Lider Młodzieży", "church", None, False, 100),
]

REMOVED_SERVICE_TYPE_SLUGS = frozenset({"mlodszy_pastor", "senior_diakon"})

SERVICE_TYPE_MIGRATIONS: dict[str, str] = {
    "mlodszy_pastor": "pastor",
    "senior_diakon": "diakon_skarbnik",
}

PASTOR_SERVICE_SLUGS = frozenset({"pastor", "senior_pastor"})

TITLE_TO_SERVICE_SLUG: dict[str, str] = {
    "pastor": "pastor",
    "diakon": "diakon",
    "diacon": "diakon",
}
