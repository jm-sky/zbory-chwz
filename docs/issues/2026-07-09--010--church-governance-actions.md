# Church governance — create, move, assign pastor

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 5)  
**Depends on:** [#007](./2026-07-09--007--acl-roles-permissions.md)

## Problem

Product rules for who may create churches, move them between regions, and assign pastors are undefined in code. These are high-impact actions that need explicit permission gates and UI.

## Scope

- [ ] Document and implement permission rules (after design review):
  - create church
  - move church between regions
  - change pastor assignment
  - create/manage branches without pastor
- [ ] API endpoints with `RequirePermission` guards
- [ ] Admin/bishop UI for governance actions
- [ ] Validation: cannot move church to region outside its community
- [ ] Optional: audit log entries for governance changes

## Acceptance criteria

- Unauthorized user gets 403 on governance endpoints
- Bishop can create church in any region of their community
- Pastor cannot move church to another region
- Branch can exist with `pastor_user_id = null` and separate branch responsible assignment

## Open questions (review before coding)

- Can Regional Bishop create churches only in their region?
- Who approves new communities (always platform admin)?
