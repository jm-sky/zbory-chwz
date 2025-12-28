"""Congregation seeder data.

This seeder creates initial congregation data for development/testing.
"""

CONGREGATIONS = [
    {
        "name": "Zbór Warszawa I",
        "description": "Zbór Warszawa I - chwz.waw.pl",
        "owner_email": "jan.madeyski@gmail.com",  # Will create user if doesn't exist
        "owner_name": "Jan Madeyski",
        "owner_role": "diakon",  # Will be stored as user role or tenant membership role
        # Address data (to be implemented in addresses module)
        "address": {
            "street": "ul. Przyce 21",
            "city": "Warszawa",
            "postal_code": None,  # Not provided
            "province": None,  # Not provided
            "country": "Poland",
        },
        # Service times (to be implemented in service_times module)
        "service_times": [
            {"day": "niedziela", "time": "11:00"},
            {"day": "środa", "time": "19:00"},
            {"day": "piątek", "time": "19:00"},
        ],
        # Website
        "website": "chwz.waw.pl",
        # Contact person (to be implemented in contact_persons module)
        "contact_person": {
            "name": "Jan Madeyski",
            "title": "Diakon",
        },
    },
]
