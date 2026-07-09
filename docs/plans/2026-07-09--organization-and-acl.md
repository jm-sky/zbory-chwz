# Organization structure and permissions (ACL)

## Separation of roles and permissions

System roles/functions describe a person's position in the church organization.
They should not directly define access rights.

Permissions are a separate layer.

```
function/role -> default permissions -> user exceptions -> final permissions
```

## Church hierarchy

A pastor can be responsible for one or more organizational units:

```
Community
└── Region
    └── Church
        └── Branch
```

Example:

```
Warszawa Centrum
└── Placówka Praga
```

A branch may exist without a pastor.

## Roles and responsibilities

Examples:

- Pastor: normally manages one or more churches.
- Diacon: may manage selected areas.
- Branch responsible person: may manage a branch without being a pastor.

A person can have different roles in different organizational units.

## Default permissions

A role/function can provide default permissions:

```
Pastor
✓ edit church
✓ manage events
✓ manage people

Diacon
✓ selected management areas

Branch responsible
✓ manage assigned branch
```

## Exceptions

Individual permissions can override defaults:

```
User
├── role: Pastor
├── church: Warszawa Centrum
└── exceptions:
    - deny: manage_people
    - allow: manage_branch
```

This allows real-world cases without making the permission model too complex.

## Recommended model

```
roles
- id
- name

role_permissions
- role_id
- permission

user_permissions
- user_id
- church_id
- permission
- effect: allow|deny
```

Permission resolution:

1. Load permissions from assigned roles.
2. Apply user-specific exceptions.
3. Check organizational scope (community, region, church, branch).

Visibility and editing permissions remain separate concepts.