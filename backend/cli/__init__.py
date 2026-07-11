"""CLI package for FastAPI project management.

This package provides Django-inspired management commands for common
development and administration tasks.

Usage:
    python -m cli --help
    python -m cli users create
    python -m cli users list
    python -m cli users delete <email>

The CLI is organized into command groups:
- users: User management (create, list, delete)
- db: Database operations (future)
- shell: Interactive shell (future)
"""

from .commands import db_app, tenants_app, test_app, users_app
from .main import app, main

# Register command groups
app.add_typer(db_app, name="db")
app.add_typer(users_app, name="users")
app.add_typer(tenants_app, name="tenants")
app.add_typer(test_app, name="test")

__all__ = ["app", "main"]
