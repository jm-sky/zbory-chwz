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
        # Status (to be implemented in addresses module)
        "status": "published",  # Published congregation
    },
    {
        "name": "Zbór w Łodzi",
        "description": "Zbór w Łodzi",
        "owner_email": "leszek.bijak@example.com",  # Placeholder email
        "owner_name": "Leszek Bijak",
        "owner_role": "pastor",
        # Address data (to be implemented in addresses module)
        "address": {
            "street": "ul. Rogozińskiego",
            "city": "Łódź",
            "postal_code": None,
            "province": None,
            "country": "Poland",
        },
        # Service times (to be implemented in service_times module)
        "service_times": [],
        # Website
        "website": None,
        # Contact person (to be implemented in contact_persons module)
        "contact_person": {
            "name": "Leszek Bijak",
            "title": "Pastor",
        },
        # Status (to be implemented in addresses module)
        "status": "need_verification",  # Placeholder - will be set when addresses module is ready
    },
    {
        "name": "Zbór w Legnicy",
        "description": "Zbór w Legnicy",
        "owner_email": "zbior.legnica@example.com",  # Placeholder email
        "owner_name": "Zbór w Legnicy",
        "owner_role": "member",
        # Address data (to be implemented in addresses module)
        "address": {
            "street": None,  # Not provided
            "city": "Legnica",
            "postal_code": None,
            "province": None,
            "country": "Poland",
        },
        # Service times (to be implemented in service_times module)
        "service_times": [],
        # Website
        "website": None,
        # Contact person (to be implemented in contact_persons module)
        "contact_person": None,
        # Status (to be implemented in addresses module)
        "status": "need_verification",  # Placeholder - will be set when addresses module is ready
    },
    {
        "name": "Zbór w Zabrzu",
        "description": "Zbór w Zabrzu",
        "owner_email": "zbior.zabrze@example.com",  # Placeholder email
        "owner_name": "Zbór w Zabrzu",
        "owner_role": "member",
        # Address data (to be implemented in addresses module)
        "address": {
            "street": None,  # Not provided
            "city": "Zabrze",
            "postal_code": None,
            "province": None,
            "country": "Poland",
        },
        # Service times (to be implemented in service_times module)
        "service_times": [],
        # Website
        "website": None,
        # Contact person (to be implemented in contact_persons module)
        "contact_person": None,
        # Status (to be implemented in addresses module)
        "status": "need_verification",  # Placeholder - will be set when addresses module is ready
    },
    {
        "name": "Zbór w Gołdapi",
        "description": "Zbór w Gołdapi",
        "owner_email": "jacek.romanowski@example.com",  # Placeholder email
        "owner_name": "Jacek Romanowski",
        "owner_role": "pastor",
        # Address data (to be implemented in addresses module)
        "address": {
            "street": "ul. Bagienna",
            "city": "Gołdap",
            "postal_code": None,
            "province": None,
            "country": "Poland",
        },
        # Service times (to be implemented in service_times module)
        "service_times": [],
        # Website
        "website": None,
        # Contact person (to be implemented in contact_persons module)
        "contact_person": {
            "name": "Jacek Romanowski",
            "title": "Pastor",
        },
        # Status (to be implemented in addresses module)
        "status": "need_verification",  # Placeholder - will be set when addresses module is ready
    },
]
