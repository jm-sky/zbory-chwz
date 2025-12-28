#!/usr/bin/env python3
"""Script to scrape congregation data from chwz.info.pl and add to seeder.

This script fetches the congregation list from https://www.chwz.info.pl/lista-zborow/
and formats it for the seeder with status 'need_verification'.
"""

import re
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def parse_service_times(text: str) -> list[dict[str, str]]:
    """Parse service times from text like 'niedziela godz. 10.00'."""
    service_times = []
    # Pattern to match day and time
    pattern = r"(\w+)\s+godz\.?\s*(\d{1,2}[:.]?\d{0,2})"
    matches = re.findall(pattern, text, re.IGNORECASE)

    day_mapping = {
        "niedziela": "niedziela",
        "poniedziałek": "poniedziałek",
        "wtorek": "wtorek",
        "środa": "środa",
        "czwartek": "czwartek",
        "piątek": "piątek",
        "sobota": "sobota",
    }

    for day, time in matches:
        day_lower = day.lower()
        if day_lower in day_mapping:
            # Normalize time format (10.00 -> 10:00, 10 -> 10:00)
            time_normalized = time.replace(".", ":")
            if ":" not in time_normalized:
                time_normalized = f"{time_normalized}:00"
            service_times.append(
                {
                    "day": day_mapping[day_lower],
                    "time": time_normalized,
                }
            )

    return service_times


def extract_email(text: str) -> str | None:
    """Extract email from text."""
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    match = re.search(email_pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    """Extract phone number from text."""
    # Pattern for Polish phone numbers
    phone_pattern = (
        r"(\+?\d{2,3}[\s-]?\d{2,3}[\s-]?\d{3}[\s-]?\d{3})|(\d{3}[\s-]?\d{3}[\s-]?\d{3})"
    )
    match = re.search(phone_pattern, text)
    if match:
        return match.group(0).strip()
    return None


def extract_website(text: str) -> str | None:
    """Extract website URL from text."""
    # Look for http:// or https:// URLs
    url_pattern = r'https?://[^\s<>"]+'
    match = re.search(url_pattern, text)
    if match:
        url = match.group(0)
        # Remove trailing punctuation
        url = url.rstrip(".,;:")
        return url
    # Also check for domain-like patterns
    domain_pattern = r"\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b"
    match = re.search(domain_pattern, text)
    if match:
        domain = match.group(0)
        if not domain.startswith("http"):
            return f"http://{domain}"
        return domain
    return None


def parse_address(text: str) -> dict[str, str | None]:
    """Parse address from text."""
    address = {
        "street": None,
        "city": None,
        "postal_code": None,
        "province": None,
        "country": "Poland",
    }

    # Remove "Adres:" prefix
    text = re.sub(r"^Adres:\s*", "", text, flags=re.IGNORECASE)

    # Look for postal code pattern (XX-XXX)
    postal_pattern = r"\b\d{2}-\d{3}\b"
    postal_match = re.search(postal_pattern, text)
    if postal_match:
        address["postal_code"] = postal_match.group(0)
        # Extract city name (usually after postal code)
        parts = text.split(postal_match.group(0), 1)
        if len(parts) > 1:
            city_part = parts[1].strip()
            # City is usually the first capitalized word(s) after postal code
            # Stop at common keywords
            city_match = re.match(
                r"^([A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+(?:\s+[A-ZĄĆĘŁŃÓŚŹŻ][a-ząćęłńóśźż]+)*)",
                city_part,
            )
            if city_match:
                city = city_match.group(0).strip()
                # Stop if we hit keywords like "Pastor", "Telefon", etc.
                stop_keywords = ["Pastor", "Telefon", "E-mail", "Nabożeństwa"]
                for keyword in stop_keywords:
                    if keyword in city:
                        city = city.split(keyword)[0].strip()
                        break
                if city:
                    address["city"] = city

    # Look for street pattern (ul. ...)
    # Match "ul. " followed by text until comma, newline, or postal code
    street_pattern = r"ul\.\s+([^,\n]+?)(?:\s*,\s*\d{2}-\d{3}|$)"
    street_match = re.search(street_pattern, text, re.IGNORECASE)
    if street_match:
        street = street_match.group(1).strip()
        # Clean up - remove any trailing keywords
        street = re.sub(
            r"\s+(Pastor|Telefon|E-mail).*$", "", street, flags=re.IGNORECASE
        )
        address["street"] = f"ul. {street}"

    return address


def scrape_congregations() -> list[dict]:
    """Scrape congregation data from chwz.info.pl."""
    url = "https://www.chwz.info.pl/lista-zborow/"
    print(f"Fetching data from {url}...")

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Find entry-content div
    entry_content = soup.find("div", class_="entry-content")
    if not entry_content:
        raise ValueError("Could not find entry-content div")

    congregations = []
    current_name = None
    current_data = {}

    # Process all elements in order
    for element in entry_content.find_all(["p", "hr", "div"], recursive=False):
        if element.name == "hr":
            # Separator - save current congregation if we have one
            if current_name and current_data:
                congregations.append(
                    create_congregation_dict(current_name, current_data)
                )
                current_name = None
                current_data = {}

        elif element.name == "p":
            text = element.get_text(separator="\n", strip=True)

            # Check if this is a congregation name (strong tag)
            strong = element.find("strong")
            if strong:
                current_name = strong.get_text(strip=True)
                current_data = {}
                continue

            # Skip empty paragraphs
            if not text or len(text) < 5:
                continue

            # Process text line by line for better parsing
            lines = [line.strip() for line in text.split("\n") if line.strip()]

            for line in lines:
                # Check if this contains service times
                if "nabożeństwa" in line.lower() or "godz." in line.lower():
                    service_times = parse_service_times(line)
                    if service_times:
                        current_data["service_times"] = service_times
                    continue

                # Check for address
                if "adres:" in line.lower():
                    address = parse_address(line)
                    if address.get("city") or address.get("street"):
                        current_data["address"] = address
                    continue

                # Check for pastor
                if "pastor:" in line.lower():
                    # Extract pastor name (everything after "Pastor:")
                    pastor_match = re.search(
                        r"Pastor:\s*(.+?)(?:\s+Telefon|\s+E-mail|$)",
                        line,
                        re.IGNORECASE,
                    )
                    if pastor_match:
                        pastor_name = pastor_match.group(1).strip()
                        # Clean up - remove any trailing punctuation or extra text
                        pastor_name = re.sub(r"[,\s]+$", "", pastor_name)
                        current_data["pastor"] = pastor_name
                    continue

                # Extract email (standalone line or after "E-mail:")
                if "e-mail:" in line.lower() or "@" in line:
                    email = extract_email(line)
                    if email:
                        # Clean email - take only the actual email address
                        email_match = re.search(
                            r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b",
                            line,
                        )
                        if email_match:
                            current_data["email"] = email_match.group(1)
                    continue

                # Extract phone (standalone line or after "Telefon:")
                if "telefon:" in line.lower() or re.search(
                    r"\d{3}[\s-]?\d{3}[\s-]?\d{3}", line
                ):
                    phone = extract_phone(line)
                    if phone:
                        current_data["phone"] = phone
                    continue

                # Extract website (standalone line or URL)
                if "http" in line.lower() or re.search(
                    r"\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b",
                    line,
                ):
                    website = extract_website(line)
                    if website:
                        current_data["website"] = website
                    continue

        elif element.name == "div" and "wp-block-columns" in element.get("class", []):
            # This is a columns container - process columns separately
            columns = element.find_all("div", class_="wp-block-column")
            for col in columns:
                text = col.get_text(separator="\n", strip=True)
                if not text:
                    continue

                lines = [line.strip() for line in text.split("\n") if line.strip()]

                for line in lines:
                    # Check if this contains service times
                    if "nabożeństwa" in line.lower() or "godz." in line.lower():
                        service_times = parse_service_times(line)
                        if service_times:
                            current_data["service_times"] = service_times
                        continue

                    # Check for address
                    if "adres:" in line.lower():
                        address = parse_address(line)
                        if address.get("city") or address.get("street"):
                            current_data["address"] = address
                        continue

                    # Check for pastor
                    if "pastor:" in line.lower():
                        pastor_match = re.search(
                            r"Pastor:\s*(.+?)(?:\s+Telefon|\s+E-mail|$)",
                            line,
                            re.IGNORECASE,
                        )
                        if pastor_match:
                            pastor_name = pastor_match.group(1).strip()
                            pastor_name = re.sub(r"[,\s]+$", "", pastor_name)
                            current_data["pastor"] = pastor_name
                        continue

                    # Extract email
                    if "e-mail:" in line.lower() or "@" in line:
                        email_match = re.search(
                            r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b",
                            line,
                        )
                        if email_match:
                            current_data["email"] = email_match.group(1)
                        continue

                    # Extract phone
                    if "telefon:" in line.lower() or re.search(
                        r"\d{3}[\s-]?\d{3}[\s-]?\d{3}", line
                    ):
                        phone = extract_phone(line)
                        if phone:
                            current_data["phone"] = phone
                        continue

                    # Extract website
                    if "http" in line.lower():
                        website = extract_website(line)
                        if website:
                            current_data["website"] = website
                        continue

    # Don't forget the last congregation
    if current_name and current_data:
        congregations.append(create_congregation_dict(current_name, current_data))

    return congregations


def create_congregation_dict(name: str, data: dict) -> dict:
    """Create a congregation dictionary from parsed data."""
    # Clean up email - use only the first valid email found
    email = data.get("email")
    if email:
        # Extract just the email address if it's mixed with other text
        email_match = re.search(
            r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b", email
        )
        if email_match:
            email = email_match.group(1)

    # Clean up pastor name
    pastor = data.get("pastor")
    if pastor:
        # Remove any trailing text after the name
        pastor = re.sub(r"\s+Telefon.*$", "", pastor, flags=re.IGNORECASE)
        pastor = re.sub(r"\s+E-mail.*$", "", pastor, flags=re.IGNORECASE)
        pastor = pastor.strip()

    # Generate owner email if not found
    owner_email = email
    if not owner_email:
        # Create a placeholder email from congregation name
        name_slug = (
            name.lower()
            .replace(" ", "-")
            .replace(",", "")
            .replace("'", "")
            .replace('"', "")
        )
        name_slug = re.sub(r"[^a-z0-9-]", "", name_slug)
        owner_email = f"zbior.{name_slug}@example.com"

    return {
        "name": name,
        "description": name,
        "owner_email": owner_email,
        "owner_name": pastor or name,
        "owner_role": "pastor" if pastor else "member",
        "address": data.get(
            "address",
            {
                "street": None,
                "city": None,
                "postal_code": None,
                "province": None,
                "country": "Poland",
            },
        ),
        "service_times": data.get("service_times", []),
        "website": data.get("website"),
        "contact_person": (
            {
                "name": pastor,
                "title": "Pastor" if pastor else None,
                "email": email,
                "phone": data.get("phone"),
            }
            if pastor
            else None
        ),
        "status": "need_verification",
    }


def format_for_seeder(congregations: list[dict]) -> str:
    """Format congregations as Python list for seeder file."""
    lines = ["CONGREGATIONS = ["]

    for i, cong in enumerate(congregations):
        lines.append("    {")
        lines.append(f'        "name": {repr(cong["name"])},')
        lines.append(f'        "description": {repr(cong["description"])},')
        lines.append(f'        "owner_email": {repr(cong["owner_email"])},')
        lines.append(f'        "owner_name": {repr(cong["owner_name"])},')
        lines.append(f'        "owner_role": {repr(cong["owner_role"])},')

        # Address
        lines.append('        "address": {')
        addr = cong["address"]
        lines.append(f'            "street": {repr(addr.get("street"))},')
        lines.append(f'            "city": {repr(addr.get("city"))},')
        lines.append(f'            "postal_code": {repr(addr.get("postal_code"))},')
        lines.append(f'            "province": {repr(addr.get("province"))},')
        lines.append(f'            "country": {repr(addr.get("country", "Poland"))},')
        lines.append("        },")

        # Service times
        lines.append('        "service_times": [')
        for st in cong.get("service_times", []):
            lines.append(
                f'            {{"day": {repr(st["day"])}, "time": {repr(st["time"])}}},'
            )
        lines.append("        ],")

        # Website
        lines.append(f'        "website": {repr(cong.get("website"))},')

        # Contact person
        if cong.get("contact_person"):
            cp = cong["contact_person"]
            lines.append('        "contact_person": {')
            lines.append(f'            "name": {repr(cp.get("name"))},')
            lines.append(f'            "title": {repr(cp.get("title"))},')
            if cp.get("email"):
                lines.append(f'            "email": {repr(cp.get("email"))},')
            if cp.get("phone"):
                lines.append(f'            "phone": {repr(cp.get("phone"))},')
            lines.append("        },")
        else:
            lines.append('        "contact_person": None,')

        # Status
        lines.append(f'        "status": {repr(cong["status"])},')

        lines.append("    }," if i < len(congregations) - 1 else "    },")

    lines.append("]")
    return "\n".join(lines)


def main():
    """Main function."""
    print("Scraping congregation data from chwz.info.pl...")

    try:
        congregations = scrape_congregations()
        print(f"Found {len(congregations)} congregations")

        # Format for seeder
        seeder_content = format_for_seeder(congregations)

        # Write to file
        output_file = (
            Path(__file__).parent.parent
            / "app"
            / "seeders"
            / "chwz_congregations_scraped.py"
        )
        output_file.write_text(
            f'"""Congregation data scraped from chwz.info.pl/lista-zborow/\n'
            f"\n"
            f"This file contains congregation data scraped from the CHWZ website.\n"
            f'All congregations have status "need_verification" and require manual review.\n'
            f'"""\n\n'
            f"{seeder_content}\n",
            encoding="utf-8",
        )

        print(f"✓ Saved {len(congregations)} congregations to {output_file}")
        print("\nTo use this data, you can:")
        print("1. Review the scraped data in the file")
        print("2. Merge it with existing CONGREGATIONS in congregations.py")
        print("3. Run: python -m cli db seed congregations")

    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
