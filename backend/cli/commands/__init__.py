"""CLI commands package.

This package contains all CLI command groups.
Each command group is defined in a separate module.
"""

from .db import db_app
from .mail import mail_app
from .tenants import tenants_app
from .test import test_app
from .users import users_app

__all__ = ["db_app", "users_app", "tenants_app", "test_app", "mail_app"]
