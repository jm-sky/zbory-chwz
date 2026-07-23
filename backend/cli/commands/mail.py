"""Clergy e-mail import CLI commands."""

import asyncio

import typer
from rich.console import Console

from ..main import COMMAND_GROUPS, show_group_interactive_menu

mail_app = typer.Typer(
    name="mail",
    help="Clergy e-mail import commands",
    no_args_is_help=False,  # We handle no-args case ourselves for interactive mode
)

console = Console()


@mail_app.callback(invoke_without_command=True)
def mail_callback(ctx: typer.Context) -> None:
    """Callback for mail command group - shows interactive menu if no subcommand provided."""
    if ctx.invoked_subcommand is None:
        show_group_interactive_menu("mail", COMMAND_GROUPS["mail"])


async def _poll_inbox_async() -> None:
    from app.core.database import get_db
    from app.modules.congregations.email_import_service import EmailImportService

    async for db in get_db():
        service = EmailImportService(db)
        result = await service.poll_and_process()
        console.print(f"[green]Poll complete:[/green] fetched={result.fetched} " f"processed={result.processed} skipped_duplicate={result.skipped_duplicate}")
        return


@mail_app.command("poll-inbox")
def poll_inbox() -> None:
    """Poll the clergy e-mail update mailbox and queue proposals for review."""
    asyncio.run(_poll_inbox_async())
