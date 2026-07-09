# Organizational hierarchy — data model

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 1)

## Problem

Congregations are modeled as flat `tenants` with no community/region/branch hierarchy. Multi-community support and scoped editorial access require a proper organizational tree.

## Scope

- [ ] Alembic migration: `communities`, `regions`, `churches`, `branches`
- [ ] `churches.legacy_tenant_id` FK for migration bridge
- [ ] `slug` columns on community, region, church, branch
- [ ] Backfill seeder/CLI: existing tenants → churches under default CHWZ community
- [ ] Repositories + admin CRUD endpoints (read-only public later)
- [ ] Pydantic schemas and basic integration tests

## Acceptance criteria

- Every existing tenant has a corresponding `church` row
- Hierarchy query works: community → regions → churches → branches
- Slugs are unique within their parent scope

## Notes

- Do not drop `tenants` in this issue — bridge only
- Default community slug: `chwz` (configurable)
