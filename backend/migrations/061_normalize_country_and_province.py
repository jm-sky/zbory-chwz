"""Migration: store country as ISO 3166-1 alpha-2, backfill city and province.

`congregation_addresses.country` held free text seeded from a scrape of
chwz.info.pl: "Poland" (31 rows) and "Polska" (2 rows), including one German
congregation. Storing the ISO code instead lets the UI render a localized
country name via `Intl.DisplayNames` and makes a country filter meaningful.

`city` is NOT NULL, so rows the scrape left without a city were seeded with the
literal string "Unknown" (13 rows). The city is recoverable from the tenant
name, which carries it in the Polish locative case ("ZBÓR W KŁODZKU").

`province` was NULL on every row but one. It is backfilled from the city.

Two rows are deliberately left alone and need a human:
  - "ZBÓR W ŚWIEBODZINIE" has city "Rzuchowa" (Świebodzin is in lubuskie,
    Rzuchowa is in małopolskie) — the scrape mismatched name and address.
  - "ZBÓR W DANKOWICACH" — several villages named Dankowice exist and the row
    has no postal code to disambiguate.

Usage:
    python migrations/061_normalize_country_and_province.py upgrade
    python migrations/061_normalize_country_and_province.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.core.database import engine

# Tenant name -> city, for rows seeded with city = "Unknown".
CITY_BY_TENANT_NAME: dict[str, str] = {
    "ZBÓR W BYSTRZYCY KŁODZKIEJ": "Bystrzyca Kłodzka",
    "ZBÓR W DANKOWICACH": "Dankowice",
    "ZBÓR W GDAŃSKU": "Gdańsk",
    "ZBÓR W GLIWICACH- ŁABĘDACH": "Gliwice",
    "ZBÓR W GOŁDAPI": "Gołdap",
    "ZBÓR W GRABÓWCE": "Grabówka",
    "ZBÓR W KĘDZIERZYNIE-KOŹLU": "Kędzierzyn-Koźle",
    "ZBÓR W KŁODZKU": "Kłodzko",
    "ZBÓR W LESZNIE": "Leszno",
    "ZBÓR W LUBINIE": "Lubin",
    "ZBÓR W MARKTREDWITZ (Freie Christengemeinde)": "Marktredwitz",
    "ZBÓR W TRZEBINI": "Trzebinia",
    "ZBÓR W ZABRZU": "Zabrze",
    "ZBÓR WE WROCŁAWIU": "Wrocław",
}

# Tenant name -> ISO country code, for congregations outside Poland.
COUNTRY_BY_TENANT_NAME: dict[str, str] = {
    "ZBÓR W MARKTREDWITZ (Freie Christengemeinde)": "DE",
}

# City -> voivodeship slug. Cities absent from this map keep province = NULL.
PROVINCE_BY_CITY: dict[str, str] = {
    "Barlinek": "zachodniopomorskie",
    "Białystok": "podlaskie",
    "Brzeg": "opolskie",
    "Bystrzyca Kłodzka": "dolnoslaskie",
    "Gdańsk": "pomorskie",
    "Gliwice": "slaskie",
    "Gołdap": "warminsko-mazurskie",
    "Grabówka": "podlaskie",
    "Kostrzyn": "lubuskie",
    "Kędzierzyn-Koźle": "opolskie",
    "Kętrzyn": "warminsko-mazurskie",
    "Kłodzko": "dolnoslaskie",
    "Legnica": "dolnoslaskie",
    "Leszno": "wielkopolskie",
    "Lubin": "dolnoslaskie",
    "Lubsko": "lubuskie",
    "Olsztyn": "warminsko-mazurskie",
    "Przemków": "dolnoslaskie",
    "Ruda Śląska": "slaskie",
    "Trzebinia": "malopolskie",
    "Warszawa": "mazowieckie",
    "Wrocław": "dolnoslaskie",
    "Wysowa": "malopolskie",
    "Zabrze": "slaskie",
    "Łódź": "lodzkie",
    "Żory": "slaskie",
}


async def upgrade() -> None:
    async with engine.begin() as conn:
        print("Backfilling city from tenant name...")
        for tenant_name, city in CITY_BY_TENANT_NAME.items():
            await conn.execute(
                text("""
                    UPDATE congregation_addresses AS a
                    SET city = :city
                    FROM tenants AS t
                    WHERE t.id = a.tenant_id
                      AND t.name = :tenant_name
                      AND a.city = 'Unknown'
                    """),
                {"city": city, "tenant_name": tenant_name},
            )

        print("Normalizing country to ISO 3166-1 alpha-2...")
        await conn.execute(text("""
                UPDATE congregation_addresses
                SET country = 'PL'
                WHERE country IN ('Poland', 'Polska')
                """))
        for tenant_name, country in COUNTRY_BY_TENANT_NAME.items():
            await conn.execute(
                text("""
                    UPDATE congregation_addresses AS a
                    SET country = :country
                    FROM tenants AS t
                    WHERE t.id = a.tenant_id AND t.name = :tenant_name
                    """),
                {"country": country, "tenant_name": tenant_name},
            )

        leftover = await conn.scalar(text("SELECT count(*) FROM congregation_addresses WHERE country !~ '^[A-Z]{2}$'"))
        if leftover:
            rows = await conn.execute(text("""
                    SELECT DISTINCT country FROM congregation_addresses
                    WHERE country !~ '^[A-Z]{2}$'
                    """))
            unmapped = ", ".join(repr(r[0]) for r in rows)
            raise RuntimeError(f"{leftover} address(es) have a country that is not an ISO code: " f"{unmapped}. Map them in COUNTRY_BY_TENANT_NAME and re-run.")

        print("Backfilling province from city...")
        for city, province in PROVINCE_BY_CITY.items():
            await conn.execute(
                text("""
                    UPDATE congregation_addresses
                    SET province = :province
                    WHERE city = :city
                      AND country = 'PL'
                      AND (province IS NULL OR lower(province) = :province)
                    """),
                {"city": city, "province": province},
            )

        print("Shrinking country column to the ISO code width...")
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ALTER COLUMN country TYPE VARCHAR(2),
                ALTER COLUMN country SET DEFAULT 'PL'
                """))

    print("Migration 061 upgrade complete.")


async def downgrade() -> None:
    async with engine.begin() as conn:
        print("Restoring free-text country column...")
        await conn.execute(text("""
                ALTER TABLE congregation_addresses
                ALTER COLUMN country TYPE VARCHAR(100),
                ALTER COLUMN country SET DEFAULT 'Poland'
                """))
        await conn.execute(text("UPDATE congregation_addresses SET country = 'Poland' WHERE country = 'PL'"))
        await conn.execute(text("UPDATE congregation_addresses SET country = 'Germany' WHERE country = 'DE'"))

    print("Migration 061 downgrade complete. City and province backfill is kept.")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
