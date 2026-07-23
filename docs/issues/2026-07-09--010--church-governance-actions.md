# Church governance — people, services, invite

**Status:** `planned`  
**Created:** 2026-07-09  
**Plan:** [2026-07-09--church-platform-implementation.md](../plans/2026-07-09--church-platform-implementation.md) (Phase 5)  
**Spec:** [2026-07-09--church-people-and-services.md](../plans/2026-07-09--church-people-and-services.md)  
**Depends on:** [#006](./2026-07-09--006--org-hierarchy-data-model.md), [#007](./2026-07-09--007--acl-roles-permissions.md)

## Scope

- [ ] People form: imię, nazwisko, email, telefon (optional) + search existing person
- [ ] Służba select + „Inna” + opis
- [ ] Checkbox „Utwórz konto” + permission picker (suggested from service, editable)
- [ ] Pastor: checkbox pre-checked, inactive account, invite action
- [ ] Create church, move region
- [ ] Remove assignment (cascade ACL via `source_assignment_id`)

## UI wireframe (logical)

```
[+ Dodaj osobę]  [🔍 Wybierz istniejącą]

Imię [    ]  Nazwisko [    ]  Email [    ]  Tel [    ]
Służba [ Diakon ▼ ]  lub Inna: [____________]
Opis   [ Skarbnik / odpowiedzialny za finanse... ]

☐ Utwórz konto użytkownika
   Uprawnienia: [podpowiedź: Diacon] [edytuj...]
```

## Acceptance criteria

- Diakon ze służbą ale bez konta — widoczny na profilu, brak logowania
- Diakon + konto + custom permissions ≠ domyślne Diacon
- Ta sama osoba dodana do drugiego zboru bez duplikacji `persons`

## Open questions

- Invite flow endpoint
