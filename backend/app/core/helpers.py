"""Helper functions for application core functionality."""

import json


def parse_list_value(v: str | list[str] | None) -> list[str]:
    """
    Parse list value from JSON array or comma-separated string.

    Supports multiple input formats:
    - JSON array string: '["localhost","127.0.0.1"]' or ["localhost","127.0.0.1"]
    - Comma-separated string: "localhost,127.0.0.1"
    - Already parsed list: ["localhost", "127.0.0.1"]
    - None: returns empty list

    Args:
        v: Input value (string, list, or None)

    Returns:
        list[str]: Parsed list of strings

    Examples:
        >>> parse_list_value('["localhost","127.0.0.1"]')
        ['localhost', '127.0.0.1']
        >>> parse_list_value("localhost,127.0.0.1")
        ['localhost', '127.0.0.1']
        >>> parse_list_value(["localhost", "127.0.0.1"])
        ['localhost', '127.0.0.1']
        >>> parse_list_value(None)
        []
    """
    if v is None:
        return []
    if isinstance(v, list):
        return [str(item) for item in v]
    if isinstance(v, str):
        # Remove surrounding quotes if present
        v = v.strip().strip('"').strip("'")
        # Try JSON first (e.g., '["localhost","127.0.0.1"]' or ["localhost","127.0.0.1"])
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except (json.JSONDecodeError, TypeError, ValueError):
            pass
        # Fall back to comma-separated string (e.g., "localhost,127.0.0.1")
        return [item.strip() for item in v.split(",") if item.strip()]
    return []
