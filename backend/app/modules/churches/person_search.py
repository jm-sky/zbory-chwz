"""Python-side person matching, shared by ChurchRepository.search_persons and
DirectoryRepository.list_persons.

PersonDB.first_name/last_name/email/phone are encrypted at rest
(app.common.crypto.encrypted_types.EncryptedString), so SQL `ILIKE` substring
matching against those columns no longer works — the database only ever sees
ciphertext. Both call sites now scope the query to allowed rows in SQL (via
service_assignments/ACL, which stays plaintext) and then decrypt the bounded
candidate set and filter it here, in Python, replicating the exact matching
rules the old SQL `ilike`/word-order conditions implemented.
"""

from __future__ import annotations

import re

# Safety valve shared by both call sites below: the community this app
# serves is small (hundreds to low thousands of persons total — not tens of
# thousands, per product confirmation), so scoping by ACL in SQL and then
# decrypting+filtering the whole in-scope set in Python is cheap. This cap
# only guards against an unexpectedly large scope (e.g. a region-wide ACL
# role) turning into an unbounded decrypt-everything pass.
SEARCH_CANDIDATE_CAP = 5000


def person_matches_query(
    *,
    first_name: str | None,
    last_name: str | None,
    email: str | None,
    phone: str | None,
    query: str,
) -> bool:
    trimmed = query.strip()
    if not trimmed:
        return False
    needle = trimmed.lower()

    if any(field and needle in field.lower() for field in (first_name, last_name, email, phone)):
        return True

    # Phone numbers are stored/typed with varying spacing ("+48 600 000 000"
    # vs "600000000") — compare digits only so formatting doesn't matter.
    phone_digits = re.sub(r"\D", "", trimmed)
    if phone_digits and phone:
        normalized_phone = re.sub(r"[\s\-()+]", "", phone)
        if phone_digits in normalized_phone:
            return True

    # "Jan Kowalski" should match a person even though first/last name are
    # separate fields — try both word orders.
    words = trimmed.split()
    if len(words) == 2 and first_name and last_name:
        word_a, word_b = words[0].lower(), words[1].lower()
        fn, ln = first_name.lower(), last_name.lower()
        if (word_a in fn and word_b in ln) or (word_b in fn and word_a in ln):
            return True

    return False
