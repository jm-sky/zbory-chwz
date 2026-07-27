"""Main API router aggregating all module routers."""

from fastapi import APIRouter, Depends

from app.core.health_details import build_health_details, verify_health_details_token

# Module routers registration
# When you add modules using 'fastapi-registry add <module>', the CLI will automatically
# add the necessary imports and include_router calls here.
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.churches.router import router as churches_router
from app.modules.congregations.import_router import (
    router as congregations_import_router,
)
from app.modules.congregations.router import router as congregations_router
from app.modules.directory.router import router as directory_router
from app.modules.google_contacts.router import router as google_contacts_router
from app.modules.governance.router import router as governance_router
from app.modules.groups.router import router as groups_router
from app.modules.logs.router import router as logs_router
from app.modules.settings.router import router as settings_router
from app.modules.sharing.router import global_router as global_share_links_router
from app.modules.sharing.router import router as sharing_router
from app.modules.stats.router import router as stats_router
from app.modules.tenants.router import (
    public_congregations_router,
    public_share_router,
)
from app.modules.tenants.router import (
    router as tenants_router,
)
from app.modules.users.router import router as users_router

# Main API router
api_router = APIRouter()


# Health check endpoint
@api_router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Status message
    """
    return {"status": "healthy"}


# Detailed health endpoint for Ops Monitor (bearer-token protected)
@api_router.get(
    "/health/details",
    tags=["Health"],
    dependencies=[Depends(verify_health_details_token)],
)
async def health_check_details() -> dict:
    """
    Detailed health check for Ops Monitor.

    Reports per-component status (database, cache, storage, frontend) per the
    ops-monitor health schema contract. Requires ``Authorization: Bearer
    <HEALTH_DETAILS_TOKEN>``.

    Returns:
        Health details response (schema_version, status, components, ...)
    """
    return await build_health_details()


# Register module routers
api_router.include_router(admin_router)
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])
api_router.include_router(logs_router, prefix="/logs", tags=["Logs", "Monitoring"])
api_router.include_router(stats_router, prefix="/stats", tags=["Statistics"])
api_router.include_router(users_router, prefix="/users", tags=["Users"])
api_router.include_router(settings_router, prefix="/me/settings", tags=["Settings"])
api_router.include_router(tenants_router)
api_router.include_router(public_congregations_router)  # Public congregations list
api_router.include_router(public_share_router)  # Anonymous share-link resolution
api_router.include_router(congregations_router)  # Authenticated congregation management (addresses, service times, contact persons)
api_router.include_router(congregations_import_router)  # Admin-only: AI-assisted address/contact import from pasted text
api_router.include_router(sharing_router)  # Congregation share-link management (create/list/revoke)
api_router.include_router(global_share_links_router)  # All-congregations share-link management (admin/owner only)
api_router.include_router(churches_router)
api_router.include_router(governance_router)
api_router.include_router(groups_router)
api_router.include_router(directory_router)
api_router.include_router(google_contacts_router)

# Register Two-Factor module (optional, added during development)
try:
    from app.modules.two_factor.router import router as two_factor_router

    api_router.include_router(
        two_factor_router,
        prefix="/two-factor",
        tags=["Two-Factor Authentication", "Security", "WebAuthn", "TOTP"],
    )
except ImportError:
    # Module may be absent in some builds; ignore if not present
    pass
