"""Tenant management CLI commands."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from ..main import COMMAND_GROUPS, show_group_interactive_menu

tenants_app = typer.Typer(
    name="tenants",
    help="Tenant management commands",
    no_args_is_help=False,  # We handle no-args case ourselves for interactive mode
)

console = Console()


@tenants_app.callback(invoke_without_command=True)
def tenants_callback(ctx: typer.Context) -> None:
    """Callback for tenants command group - shows interactive menu if no subcommand provided."""
    if ctx.invoked_subcommand is None:
        # No subcommand provided, show interactive menu
        show_group_interactive_menu("tenants", COMMAND_GROUPS["tenants"])


async def _create_tenant_async(name: str, description: str | None, owner_email: str) -> None:
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository
    from app.modules.tenants.repositories import TenantRepository

    async for db in get_db():
        tenant_repo = TenantRepository(db)
        user_repo = UserRepository(db)

        owner = await user_repo.get_user_by_email(owner_email)
        if owner is None:
            console.print(f"[red]User with email {owner_email} not found[/red]")
            raise typer.Exit(1)

        tenant, membership = await tenant_repo.create_tenant(
            name=name,
            description=description,
            owner_user_id=owner.id,
        )
        console.print(f"[green]Tenant created:[/green] {tenant.name} ({tenant.id}) owner={membership.user_id}")
        return


async def _assign_member_async(tenant_id: str, email: str, role: str) -> None:
    from app.core.database import get_db
    from app.modules.auth.repositories import UserRepository
    from app.modules.tenants.repositories import TenantRepository

    async for db in get_db():
        tenant_repo = TenantRepository(db)
        user_repo = UserRepository(db)

        tenant = await tenant_repo.get_tenant(tenant_id)
        if tenant is None:
            console.print(f"[red]Tenant {tenant_id} not found[/red]")
            raise typer.Exit(1)

        user = await user_repo.get_user_by_email(email)
        if user is None:
            console.print(f"[red]User {email} not found[/red]")
            raise typer.Exit(1)

        membership = await tenant_repo.add_member(tenant_id=tenant_id, user_id=user.id, role=role)
        console.print(f"[green]Assigned[/green] {email} -> {tenant.name} as {membership.role}")
        return


async def _list_tenants_async() -> None:
    from app.core.database import get_db
    from app.modules.tenants.repositories import TenantRepository

    async for db in get_db():
        tenant_repo = TenantRepository(db)
        tenants = await tenant_repo.list_all()

        table = Table(title="Tenants", show_lines=True)
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Description")
        table.add_column("Owner ID")
        table.add_column("Created")

        for tenant in tenants:
            table.add_row(tenant.id, tenant.name, tenant.description or "-", tenant.owner_id, tenant.created_at.isoformat())

        console.print(table)
        return


@tenants_app.command("create")
def create_tenant(
    name: str = typer.Argument(..., help="Tenant name"),
    email: str = typer.Option(..., "--owner-email", "-e", prompt=True, help="Owner email"),
    description: str | None = typer.Option(None, "--description", "-d", help="Tenant description"),
) -> None:
    """Create tenant and assign owner."""
    asyncio.run(_create_tenant_async(name=name, description=description, owner_email=email))


@tenants_app.command("assign")
def assign_member(
    tenant_id: str = typer.Argument(..., help="Tenant identifier"),
    email: str = typer.Argument(..., help="User email"),
    role: str = typer.Option("member", "--role", "-r", help="Membership role"),
) -> None:
    """Assign an existing user to tenant."""
    asyncio.run(_assign_member_async(tenant_id=tenant_id, email=email, role=role))


@tenants_app.command("list")
def list_tenants() -> None:
    """List all tenants."""
    asyncio.run(_list_tenants_async())
