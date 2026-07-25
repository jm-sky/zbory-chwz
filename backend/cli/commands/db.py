"""Database management CLI commands."""

import asyncio
import importlib.util
import sys
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console
from rich.prompt import Confirm
from rich.table import Table

from ..main import COMMAND_GROUPS, show_group_interactive_menu

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

db_app = typer.Typer(
    name="db",
    help="Database management commands",
    no_args_is_help=False,  # We handle no-args case ourselves for interactive mode
)

console = Console()


@db_app.callback(invoke_without_command=True)
def db_callback(ctx: typer.Context) -> None:
    """Callback for db command group - shows interactive menu if no subcommand provided."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show interactive menu
        show_group_interactive_menu("db", COMMAND_GROUPS["db"])


MODEL_MODULES = [
    "app.modules.auth.db_models",
    "app.modules.users.db_models",
    "app.modules.logs.db_models",
    "app.modules.settings.db_models",
    "app.modules.tenants.db_models",
    "app.modules.two_factor.db_models",
]


def _import_model_modules() -> None:
    """Ensure all SQLAlchemy models are imported before create_all."""
    for module_path in MODEL_MODULES:
        try:
            import_module(module_path)
        except ModuleNotFoundError:
            console.print(f"[yellow]Skipping missing module:[/yellow] {module_path}")


@db_app.command("init")
def init_database(force: bool = typer.Option(False, "--force", "-f", help="Recreate database file if it already exists")) -> None:
    """Initialize application database (run SQLAlchemy metadata create_all)."""

    async def _init() -> None:
        _import_model_modules()

        # Import SchemaMigration model to ensure it's included in metadata
        from app.core.database import Base, engine, init_db
        from app.core.migrations import SchemaMigration  # noqa: F401

        if force:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)

        await init_db()

        # Mark migration 000 as applied if it wasn't already
        from app.core.migrations import ensure_schema_migrations_table, is_migration_applied, mark_migration_as_applied

        await ensure_schema_migrations_table()
        if not await is_migration_applied("000"):
            await mark_migration_as_applied("000", "create_schema_migrations")
            console.print("[green]✓ Migration 000 marked as applied[/green]")

    db_path = Path(__file__).resolve().parents[2] / "data" / "app.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists() and not force:
        console.print(f"[yellow]Database already exists at[/yellow] {db_path}")
        if not Confirm.ask("Re-run initialization anyway?", default=True):
            console.print("[yellow]Cancelled[/yellow]")
            raise typer.Exit()

    console.print("[bold green]Initializing database...[/bold green]")
    asyncio.run(_init())
    console.print(f"[bold green]✓ Database ready:[/bold green] {db_path}")


@db_app.command("migrate")
def migrate_database(
    fake: bool = typer.Option(False, "--fake", help="Mark migrations as applied without running them"),
    skip_init_check: bool = typer.Option(False, "--skip-init-check", help="Skip automatic init if database is not initialized"),
) -> None:
    """Run all pending migrations in order.

    Automatically runs 'db init' if database is not initialized.
    """

    async def _migrate() -> None:
        from app.core.migrations import (
            discover_migrations,
            ensure_schema_migrations_table,
            get_applied_migrations,
            is_database_initialized,
            is_migration_applied,
            mark_migration_as_applied,
        )

        # Check if database is initialized, if not run init first
        if not skip_init_check:
            if not await is_database_initialized():
                console.print("[yellow]Database is not initialized. Running 'db init' first...[/yellow]")
                # Run init logic
                _import_model_modules()
                from app.core.database import init_db
                from app.core.migrations import SchemaMigration  # noqa: F401

                await init_db()

                # Mark migration 000 as applied
                await ensure_schema_migrations_table()
                if not await is_migration_applied("000"):
                    await mark_migration_as_applied("000", "create_schema_migrations")
                    console.print("[green]✓ Migration 000 marked as applied[/green]")

                console.print("[bold green]✓ Database initialized[/bold green]\n")

        # Ensure schema_migrations table exists
        await ensure_schema_migrations_table()

        # Get migrations directory
        migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
        if not migrations_dir.exists():
            console.print(f"[red]Migrations directory not found:[/red] {migrations_dir}")
            raise typer.Exit(1)

        # Discover all migrations
        all_migrations = discover_migrations(migrations_dir)
        if not all_migrations:
            console.print("[yellow]No migrations found[/yellow]")
            return

        # Get applied migrations
        applied_versions = set(await get_applied_migrations())

        # Find pending migrations
        pending_migrations = [(version, name, filepath) for version, name, filepath in all_migrations if version not in applied_versions]

        if not pending_migrations:
            console.print("[bold green]✓ All migrations are already applied[/bold green]")
            return

        console.print(f"[bold]Found {len(pending_migrations)} pending migration(s)[/bold]")

        # Run pending migrations in order
        for version, name, filepath in pending_migrations:
            console.print(f"\n[bold cyan]Running migration {version}: {name}[/bold cyan]")

            if fake:
                # Just mark as applied without running
                await mark_migration_as_applied(version, name)
                console.print(f"[yellow]Fake: Marked {version} as applied[/yellow]")
                continue

            try:
                # Import and run migration
                spec = importlib.util.spec_from_file_location(f"migration_{version}", filepath)
                if spec is None or spec.loader is None:
                    console.print(f"[red]Failed to load migration:[/red] {filepath}")
                    raise typer.Exit(1)

                migration_module = importlib.util.module_from_spec(spec)
                sys.modules[f"migration_{version}"] = migration_module
                spec.loader.exec_module(migration_module)

                # Run upgrade function
                if not hasattr(migration_module, "upgrade"):
                    console.print(f"[red]Migration {version} does not have upgrade() function[/red]")
                    raise typer.Exit(1)

                await migration_module.upgrade()

                # Mark as applied
                await mark_migration_as_applied(version, name)
                console.print(f"[bold green]✓ Migration {version} applied successfully[/bold green]")

            except Exception as e:
                console.print(f"[red]✗ Migration {version} failed:[/red] {e}")
                raise typer.Exit(1) from None

        console.print("\n[bold green]✓ All pending migrations completed[/bold green]")

    asyncio.run(_migrate())


@db_app.command("migrate-status")
def migrate_status() -> None:
    """Show status of all migrations."""

    async def _status() -> None:
        from app.core.migrations import (
            discover_migrations,
            ensure_schema_migrations_table,
            get_applied_migrations,
        )

        # Ensure schema_migrations table exists
        await ensure_schema_migrations_table()

        # Get migrations directory
        migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
        if not migrations_dir.exists():
            console.print(f"[red]Migrations directory not found:[/red] {migrations_dir}")
            raise typer.Exit(1)

        # Discover all migrations
        all_migrations = discover_migrations(migrations_dir)
        if not all_migrations:
            console.print("[yellow]No migrations found[/yellow]")
            return

        # Get applied migrations
        applied_versions = set(await get_applied_migrations())

        # Create table
        table = Table(title="Migration Status")
        table.add_column("Version", style="cyan", no_wrap=True)
        table.add_column("Name", style="magenta")
        table.add_column("Status", style="green")

        pending_count = 0
        applied_count = 0

        for version, name, _ in all_migrations:
            if version in applied_versions:
                status = "[green]✓ Applied[/green]"
                applied_count += 1
            else:
                status = "[yellow]○ Pending[/yellow]"
                pending_count += 1

            table.add_row(version, name, status)

        console.print(table)
        console.print(f"\n[bold]Total: {len(all_migrations)}[/bold] | [green]Applied: {applied_count}[/green] | [yellow]Pending: {pending_count}[/yellow]")

    asyncio.run(_status())


@db_app.command("migrate-graceful")
def migrate_graceful(
    from_version: str | None = typer.Option(None, "--from", help="Start from specific migration version (e.g., '020')"),
    skip_init_check: bool = typer.Option(False, "--skip-init-check", help="Skip automatic init if database is not initialized"),
) -> None:
    """Run migrations gracefully, ignoring errors and continuing.

    This command is useful when migrations were created in wrong order or
    filenames were changed. It will attempt to run migrations but continue
    even if errors occur.

    If --from is provided, it will unmark that migration and all subsequent
    ones, then re-run them. If --from is not provided, it will run all
    pending migrations.

    Examples:
        cli db migrate-graceful                    # Run all pending migrations
        cli db migrate-graceful --from 020         # Re-run from migration 020 onwards
    """

    async def _migrate_graceful() -> None:
        from app.core.migrations import (
            discover_migrations,
            ensure_schema_migrations_table,
            get_applied_migrations,
            is_database_initialized,
            is_migration_applied,
            mark_migration_as_applied,
            unmark_migration,
        )

        # Check if database is initialized, if not run init first
        if not skip_init_check:
            if not await is_database_initialized():
                console.print("[yellow]Database is not initialized. Running 'db init' first...[/yellow]")
                # Run init logic
                _import_model_modules()
                from app.core.database import init_db
                from app.core.migrations import SchemaMigration  # noqa: F401

                await init_db()

                # Mark migration 000 as applied
                await ensure_schema_migrations_table()
                if not await is_migration_applied("000"):
                    await mark_migration_as_applied("000", "create_schema_migrations")
                    console.print("[green]✓ Migration 000 marked as applied[/green]")

                console.print("[bold green]✓ Database initialized[/bold green]\n")

        # Ensure schema_migrations table exists
        await ensure_schema_migrations_table()

        # Get migrations directory
        migrations_dir = Path(__file__).resolve().parents[2] / "migrations"
        if not migrations_dir.exists():
            console.print(f"[red]Migrations directory not found:[/red] {migrations_dir}")
            raise typer.Exit(1)

        # Discover all migrations
        all_migrations = discover_migrations(migrations_dir)
        if not all_migrations:
            console.print("[yellow]No migrations found[/yellow]")
            return

        # Get applied migrations
        applied_versions = set(await get_applied_migrations())

        # If --from is provided, unmark that migration and all subsequent ones
        if from_version:
            console.print(f"[bold yellow]Unmarking migrations from {from_version} onwards...[/bold yellow]")
            unmarked_count = 0
            for version, _, _ in all_migrations:
                try:
                    # Compare versions numerically
                    version_float = float(version)
                    from_float = float(from_version)
                    if version_float >= from_float:
                        if await is_migration_applied(version):
                            await unmark_migration(version)
                            console.print(f"[yellow]Unmarked migration {version}[/yellow]")
                            unmarked_count += 1
                            applied_versions.discard(version)
                except ValueError:
                    # If version comparison fails, use string comparison
                    if version >= from_version:
                        if await is_migration_applied(version):
                            await unmark_migration(version)
                            console.print(f"[yellow]Unmarked migration {version}[/yellow]")
                            unmarked_count += 1
                            applied_versions.discard(version)

            if unmarked_count > 0:
                console.print(f"[bold yellow]✓ Unmarked {unmarked_count} migration(s)[/bold yellow]\n")
            else:
                console.print(f"[yellow]No migrations found to unmark from version {from_version}[/yellow]\n")

        # Find migrations to run
        # If --from was provided, we want to run from that version onwards
        # Otherwise, run all pending migrations
        migrations_to_run: list[tuple[str, str, Path]] = []
        for version, name, filepath in all_migrations:
            if from_version:
                # Check if this migration should be run (>= from_version)
                try:
                    version_float = float(version)
                    from_float = float(from_version)
                    if version_float >= from_float:
                        migrations_to_run.append((version, name, filepath))
                except ValueError:
                    if version >= from_version:
                        migrations_to_run.append((version, name, filepath))
            else:
                # Run all pending migrations
                if version not in applied_versions:
                    migrations_to_run.append((version, name, filepath))

        if not migrations_to_run:
            console.print("[bold green]✓ No migrations to run[/bold green]")
            return

        console.print(f"[bold]Found {len(migrations_to_run)} migration(s) to run gracefully[/bold]")

        # Run migrations gracefully (ignore errors)
        success_count = 0
        error_count = 0
        skipped_count = 0

        for version, name, filepath in migrations_to_run:
            console.print(f"\n[bold cyan]Running migration {version}: {name}[/bold cyan]")

            try:
                # Import and run migration
                spec = importlib.util.spec_from_file_location(f"migration_{version}", filepath)
                if spec is None or spec.loader is None:
                    console.print(f"[red]Failed to load migration:[/red] {filepath}")
                    error_count += 1
                    continue

                migration_module = importlib.util.module_from_spec(spec)
                sys.modules[f"migration_{version}"] = migration_module
                spec.loader.exec_module(migration_module)

                # Run upgrade function
                if not hasattr(migration_module, "upgrade"):
                    console.print(f"[red]Migration {version} does not have upgrade() function[/red]")
                    error_count += 1
                    continue

                await migration_module.upgrade()

                # Mark as applied (even if it was already applied, this is safe)
                await mark_migration_as_applied(version, name)
                console.print(f"[bold green]✓ Migration {version} applied successfully[/bold green]")
                success_count += 1

            except Exception as e:
                console.print(f"[yellow]⚠ Migration {version} failed (continuing):[/yellow] {e}")
                error_count += 1
                # Don't mark as applied if it failed
                # But check if it was already applied before
                if await is_migration_applied(version):
                    console.print(f"[yellow]  Note: Migration {version} was already marked as applied in database[/yellow]")
                    skipped_count += 1

        console.print("\n[bold]Migration summary:[/bold]")
        console.print(f"  [green]✓ Success: {success_count}[/green]")
        if error_count > 0:
            console.print(f"  [yellow]⚠ Errors (ignored): {error_count}[/yellow]")
        if skipped_count > 0:
            console.print(f"  [yellow]○ Skipped (already applied): {skipped_count}[/yellow]")
        console.print("\n[bold green]✓ Graceful migration completed[/bold green]")

    asyncio.run(_migrate_graceful())


@db_app.command("migrate-unmark")
def migrate_unmark(
    version: str = typer.Argument(..., help="Migration version to unmark (e.g., '020')"),
) -> None:
    """Remove a migration from schema_migrations table.

    This allows re-running a migration that was already marked as applied.
    Useful when migration files were renamed or need to be re-executed.

    Example:
        cli db migrate-unmark 020
    """

    async def _unmark() -> None:
        from app.core.migrations import (
            ensure_schema_migrations_table,
            is_migration_applied,
            unmark_migration,
        )

        # Ensure schema_migrations table exists
        await ensure_schema_migrations_table()

        # Check if migration is applied
        if not await is_migration_applied(version):
            console.print(f"[yellow]Migration {version} is not marked as applied[/yellow]")
            return

        # Unmark migration
        await unmark_migration(version)
        console.print(f"[bold green]✓ Migration {version} unmarked successfully[/bold green]")
        console.print(f"[yellow]You can now re-run it with:[/yellow] cli db migrate-graceful --from {version}")

    asyncio.run(_unmark())


@db_app.command("seed")
def seed_database(
    seeder: str = typer.Argument(..., help="Seeder name (e.g., 'congregations')"),
) -> None:
    """Seed database with initial data.

    This command populates the database with predefined seed data.
    Currently supports:
    - congregations: Congregations/churches with addresses and service times
    """

    async def _seed() -> None:
        from app.core.database import get_db

        # Get database session
        async for db in get_db():
            if seeder == "congregations":
                await _seed_congregations(db)
            else:
                console.print(f"[red]Unknown seeder: {seeder}[/red]")
                console.print("[yellow]Available seeders: congregations[/yellow]")
                raise typer.Exit(1)

            break  # Exit after first db session

    console.print(f"[bold green]Starting database seeding for '{seeder}'...[/bold green]")
    asyncio.run(_seed())
    console.print("[bold green]✓ Database seeding complete[/bold green]")


async def _seed_congregations(db: "AsyncSession") -> None:
    """Seed congregations with addresses, service times, and service contacts."""
    from sqlalchemy import select

    from app.common.id_utils import generate_id
    from app.modules.auth.db_models import UserDB
    from app.modules.auth.repositories import UserRepository
    from app.modules.churches.backfill import _ensure_service_types
    from app.modules.churches.contact_sync import upsert_primary_card_contact
    from app.modules.churches.provisioning import provision_church_for_tenant
    from app.modules.churches.repositories import ChurchRepository
    from app.modules.congregations.geo import DEFAULT_COUNTRY
    from app.modules.congregations.repositories import CongregationRepository
    from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
    from app.seeders import CONGREGATIONS

    console.print("[bold cyan]Seeding congregations...[/bold cyan]")

    user_repo = UserRepository(db)
    congregation_repo = CongregationRepository(db)
    church_repo = ChurchRepository(db)
    service_type_stats: dict[str, int] = {"service_types": 0}
    await _ensure_service_types(db, service_type_stats)

    created_count = 0
    updated_count = 0

    for cong_data in CONGREGATIONS:
        name = cong_data["name"]
        description = cong_data.get("description", "")
        owner_email = cong_data["owner_email"]
        owner_name = cong_data["owner_name"]
        website = cong_data.get("website")

        # Build description with website if provided
        full_description = description
        if website:
            if full_description:
                full_description += f" | Website: {website}"
            else:
                full_description = f"Website: {website}"

        # Find or create owner user
        owner = await user_repo.get_user_by_email(owner_email)
        if owner is None:
            console.print(f"[yellow]Creating user for owner: {owner_email}[/yellow]")
            # Create user with a temporary password (should be changed)
            # Note: This creates an unverified user - in production, use proper user creation flow
            owner_id = generate_id()
            owner = UserDB(
                id=owner_id,
                email=owner_email,
                name=owner_name,
                is_active=True,
                is_email_verified=False,  # User should verify email
            )
            db.add(owner)
            await db.commit()
            await db.refresh(owner)
            console.print(f"[green]  Created user: {owner_name} ({owner_email})[/green]")
        else:
            console.print(f"[cyan]  Using existing user: {owner_name} ({owner_email})[/cyan]")

        # Check if tenant already exists by name
        result = await db.execute(select(TenantDB).where(TenantDB.name == name))
        existing_tenant = result.scalar_one_or_none()

        # Get address, service times, and service contact data
        address_data = cong_data.get("address")
        service_times = cong_data.get("service_times", [])
        service_contact = cong_data.get("service_contact")
        status = cong_data.get("status", "draft")

        tenant_record: TenantDB
        if existing_tenant:
            # Update existing tenant
            existing_tenant.description = full_description
            existing_tenant.owner_id = owner.id
            existing_tenant.status = status
            tenant_id = existing_tenant.id
            tenant_record = existing_tenant
            updated_count += 1
            console.print(f"[yellow]  Updated tenant: {name}[/yellow]")
        else:
            # Create new tenant
            tenant_id = generate_id()
            tenant = TenantDB(
                id=tenant_id,
                name=name,
                description=full_description,
                owner_id=owner.id,
                status=status,
            )
            db.add(tenant)
            tenant_record = tenant

            # Create owner membership
            membership = TenantMembershipDB(
                tenant_id=tenant_id,
                user_id=owner.id,
                role="owner",
            )
            db.add(membership)

            created_count += 1
            console.print(f"[green]  Created tenant: {name} (ID: {tenant_id})[/green]")

            # Commit tenant and membership first so foreign keys work
            await db.commit()
            await db.refresh(tenant)

        await provision_church_for_tenant(db, tenant_record)

        # Create or update address, service times, and service contact (for both new and existing tenants)
        # Create/update address
        if address_data:
            city = address_data.get("city")
            if not city:
                # Seeding a placeholder city silently poisons the city and province
                # filters; fix the seeder entry instead.
                raise ValueError(f"Congregation {name!r} has no city in the seeder data")

            address = await congregation_repo.create_or_update_address(
                tenant_id=tenant_id,
                street=address_data.get("street"),
                city=city,
                postal_code=address_data.get("postal_code"),
                province=address_data.get("province"),
                country=address_data.get("country", DEFAULT_COUNTRY),
                status=status,
            )
            console.print(f"[cyan]    Created/updated address: {address.city}[/cyan]")

        # Delete existing service times and create new ones
        if service_times:
            await congregation_repo.delete_all_service_times(tenant_id)
            for idx, st in enumerate(service_times):
                await congregation_repo.create_service_time(
                    tenant_id=tenant_id,
                    day=st.get("day", ""),
                    time=st.get("time", ""),
                    order=idx,
                )
            times_str = ", ".join([f"{st['day']} {st['time']}" for st in service_times])
            console.print(f"[cyan]    Created service times: {times_str}[/cyan]")

        if service_contact:
            await upsert_primary_card_contact(
                church_repo,
                tenant_id,
                name=service_contact.get("name", ""),
                title=service_contact.get("title"),
                phone=service_contact.get("phone"),
                email=service_contact.get("email"),
            )
            console.print(f"[cyan]    Created service contact: {service_contact.get('name')} " f"({service_contact.get('title')})[/cyan]")

        from app.modules.churches.bishop_seed import ensure_pastor_acl_for_owner

        await ensure_pastor_acl_for_owner(
            db,
            user_id=owner.id,
            church_id=tenant_id,
        )

    from app.modules.churches.bishop_seed import seed_bishops

    bishops = await seed_bishops(db)
    console.print(f"[cyan]  Bishop seed: {bishops} new service assignment(s)[/cyan]")

    await db.commit()
    console.print(f"[bold green]✓ Created {created_count}, updated {updated_count} congregations[/bold green]")


@db_app.command("seed-remove")
def remove_seeder(
    seeder: str = typer.Argument(..., help="Seeder name to remove (e.g., 'congregations')"),
) -> None:
    """Remove seeded data from database.

    This command removes seeded data from the database.
    Currently supports:
    - congregations: Remove seeded congregations (WARNING: Also removes associated users if created by seeder)
    """

    async def _remove() -> None:
        from app.core.database import get_db

        # Get database session
        async for db in get_db():
            if seeder == "congregations":
                await _remove_congregations(db)
            else:
                console.print(f"[red]Unknown seeder: {seeder}[/red]")
                console.print("[yellow]Available seeders: congregations[/yellow]")
                raise typer.Exit(1)

            break  # Exit after first db session

    if not Confirm.ask(f"[bold red]Are you sure you want to remove all '{seeder}' data?[/bold red]", default=False):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit()

    console.print(f"[bold yellow]Removing '{seeder}' data...[/bold yellow]")
    asyncio.run(_remove())
    console.print("[bold green]✓ Data removal complete[/bold green]")


async def _remove_congregations(db: "AsyncSession") -> None:
    """Remove seeded congregations and their memberships.

    Note: This does NOT delete users that were created by the seeder.
    Users must be deleted manually if desired.
    """
    from sqlalchemy import delete, select

    from app.modules.tenants.db_models import TenantDB, TenantMembershipDB
    from app.seeders import CONGREGATIONS

    # Get list of seeded congregation names
    seeded_names = [cong["name"] for cong in CONGREGATIONS]

    # Find tenants with matching names
    result = await db.execute(select(TenantDB).where(TenantDB.name.in_(seeded_names)))
    tenants = result.scalars().all()
    tenant_ids = [tenant.id for tenant in tenants]

    if not tenant_ids:
        console.print("[yellow]No seeded congregations found[/yellow]")
        return

    # Count memberships
    result = await db.execute(select(TenantMembershipDB).where(TenantMembershipDB.tenant_id.in_(tenant_ids)))
    memberships_count = len(result.scalars().all())

    console.print(f"[yellow]Deleting {len(tenant_ids)} congregations and {memberships_count} memberships...[/yellow]")

    # Delete memberships first (CASCADE should handle this, but let's be explicit)
    await db.execute(delete(TenantMembershipDB).where(TenantMembershipDB.tenant_id.in_(tenant_ids)))
    await db.execute(delete(TenantDB).where(TenantDB.id.in_(tenant_ids)))
    await db.commit()

    console.print(f"[bold green]✓ Removed {len(tenant_ids)} congregations and {memberships_count} memberships[/bold green]")
    console.print("[yellow]Note: Users created by the seeder were NOT deleted. Delete them manually if desired.[/yellow]")


@db_app.command("churches-backfill")
def churches_backfill() -> None:
    """Backfill church hierarchy from existing tenants (idempotent)."""

    async def _run() -> None:
        from app.core.database import AsyncSessionLocal
        from app.modules.churches.backfill import backfill_churches
        from app.modules.churches.repositories import ChurchRepository

        async with AsyncSessionLocal() as db:
            repo = ChurchRepository(db)
            stats = await backfill_churches(repo)
            console.print("[bold green]Church backfill complete[/bold green]")
            for key, value in stats.items():
                console.print(f"  {key}: {value}")

    asyncio.run(_run())
