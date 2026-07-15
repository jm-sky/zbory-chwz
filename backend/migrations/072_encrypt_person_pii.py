"""Migration: encrypt PII at rest for persons and congregation_addresses.

Widens the columns that will hold ciphertext (Postgres only — SQLite columns
are already untyped/unbounded), adds blind-index columns for exact-match
lookups (persons.email_bidx, persons.phone_bidx), then encrypts any
still-plaintext rows in place via raw SQL UPDATEs.

Raw SQL rather than "read through the ORM and re-save" for the row rewrite:
SQLAlchemy's dirty-tracking compares the *decrypted* Python value, so
re-assigning a value equal to what was just read (which is always the true
plaintext, even pre-migration — see EncryptedString.process_result_value's
InvalidToken fallback) would not be considered a change and wouldn't emit an
UPDATE at all. Encrypting explicitly and writing the ciphertext directly
avoids relying on that.

Idempotent: rows whose current value already decrypts as a valid Fernet
token (i.e. a previous run already encrypted them) are left untouched, so
this is safe to re-run after an interruption.

Usage:
    python migrations/072_encrypt_person_pii.py upgrade
    python migrations/072_encrypt_person_pii.py downgrade
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from app.common.crypto.encrypted_types import (
    encrypt_value,
    hmac_email,
    hmac_phone_digits,
    is_encrypted_value,
)
from app.core.database import AsyncSessionLocal, engine

BATCH_SIZE = 200

_PERSON_TEXT_COLUMNS = ("first_name", "last_name", "email", "phone")
_ADDRESS_TEXT_COLUMNS = ("street", "city", "postal_code", "province")


async def column_exists(conn, table_name: str, column_name: str) -> bool:
    result = await conn.execute(
        text("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = :table_name
                AND column_name = :column_name
            );
        """),
        {"table_name": table_name, "column_name": column_name},
    )
    return result.scalar() is True


async def _widen_columns_for_ciphertext(conn) -> None:
    """Fernet ciphertext is considerably longer than the plaintext it
    replaces (a 255-char name encrypts to 400+ chars) — a bounded VARCHAR
    would truncate/reject it. SQLite columns are dynamically typed and don't
    need this."""
    if conn.dialect.name != "postgresql":
        print("  Note: non-PostgreSQL dialect detected — skipping column widening (already unbounded)")
        return

    for table, columns in (("persons", _PERSON_TEXT_COLUMNS), ("congregation_addresses", _ADDRESS_TEXT_COLUMNS)):
        for column in columns:
            await conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE TEXT"))
    print("  ✓ Widened persons/congregation_addresses text columns to TEXT")


async def _add_blind_index_columns(conn) -> None:
    for column in ("email_bidx", "phone_bidx"):
        if not await column_exists(conn, "persons", column):
            await conn.execute(text(f"ALTER TABLE persons ADD COLUMN {column} VARCHAR(64)"))
            print(f"  ✓ Added persons.{column}")
        else:
            print(f"  ⊙ persons.{column} already exists, skipping")

    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_persons_email_bidx ON persons(email_bidx)"))
    await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_persons_phone_bidx ON persons(phone_bidx)"))


async def _encrypt_persons() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id, first_name, last_name, email, phone FROM persons"))
        rows = result.fetchall()

    encrypted = 0
    async with AsyncSessionLocal() as session:
        for i, row in enumerate(rows):
            person_id, first_name, last_name, email, phone = row
            updates: dict[str, str | None] = {}

            if first_name is not None and not is_encrypted_value(first_name):
                updates["first_name"] = encrypt_value(first_name)
            if last_name is not None and not is_encrypted_value(last_name):
                updates["last_name"] = encrypt_value(last_name)

            # Blank-string emails predate the encrypted column and its
            # isnot(None)-only export filter — normalize to NULL here rather
            # than encrypting "" into a non-empty (but still "blank")
            # ciphertext that isnot(None) would then wrongly include.
            normalized_email = (email or "").strip() or None
            if normalized_email is None:
                if email is not None:
                    updates["email"] = None
                    updates["email_bidx"] = None
            elif not is_encrypted_value(normalized_email):
                updates["email"] = encrypt_value(normalized_email)
                updates["email_bidx"] = hmac_email(normalized_email)

            if phone is not None and not is_encrypted_value(phone):
                updates["phone"] = encrypt_value(phone)
                updates["phone_bidx"] = hmac_phone_digits(phone)

            if updates:
                set_clause = ", ".join(f"{col} = :{col}" for col in updates)
                await session.execute(text(f"UPDATE persons SET {set_clause} WHERE id = :id"), {**updates, "id": person_id})
                encrypted += 1

            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()

    return encrypted


async def _encrypt_addresses() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT id, street, city, postal_code, province FROM congregation_addresses"))
        rows = result.fetchall()

    encrypted = 0
    async with AsyncSessionLocal() as session:
        for i, row in enumerate(rows):
            address_id, street, city, postal_code, province = row
            updates: dict[str, str | None] = {}

            if street is not None and not is_encrypted_value(street):
                updates["street"] = encrypt_value(street)
            if city is not None and not is_encrypted_value(city):
                updates["city"] = encrypt_value(city)
            if postal_code is not None and not is_encrypted_value(postal_code):
                updates["postal_code"] = encrypt_value(postal_code)
            if province is not None and not is_encrypted_value(province):
                updates["province"] = encrypt_value(province)

            if updates:
                set_clause = ", ".join(f"{col} = :{col}" for col in updates)
                await session.execute(text(f"UPDATE congregation_addresses SET {set_clause} WHERE id = :id"), {**updates, "id": address_id})
                encrypted += 1

            if (i + 1) % BATCH_SIZE == 0:
                await session.commit()
        await session.commit()

    return encrypted


async def upgrade() -> None:
    print("Encrypting PII at rest (persons, congregation_addresses)...")

    async with engine.begin() as conn:
        await _add_blind_index_columns(conn)
        await _widen_columns_for_ciphertext(conn)

    persons_count = await _encrypt_persons()
    print(f"  ✓ Encrypted {persons_count} persons row(s)")

    addresses_count = await _encrypt_addresses()
    print(f"  ✓ Encrypted {addresses_count} congregation_addresses row(s)")

    print("Migration 072 upgrade complete")


async def downgrade() -> None:
    """Not supported: decrypting back to plaintext columns is a deliberately
    unsupported operation for a PII-encryption migration — undo by restoring
    from a pre-migration backup instead."""
    print("Migration 072 downgrade is not supported — restore from backup if you need to revert.")
    raise SystemExit(1)


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "upgrade"
    if command == "upgrade":
        asyncio.run(upgrade())
    elif command == "downgrade":
        asyncio.run(downgrade())
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
