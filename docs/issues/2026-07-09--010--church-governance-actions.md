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

## Decisions (2026-07-25)

- **Invite flow:** `POST /churches/{church_id}/service-assignments/{assignment_id}/invite`, za tym
  samym uprawnieniem co utworzenie przypisania (patrz
  [acl-architecture.md §5.2](../plans/2026-07-25--acl-architecture.md)). Wysyła jednorazowy token
  ustawienia hasła na adres osoby; aktywacja konta (`is_active = true`) następuje po ustawieniu
  hasła. **ACL nadaje się przy tworzeniu przypisania, nie przy aktywacji** — zgodnie z decyzją
  z 2026-07-09 („Pastor ACL before `is_active`”), więc invite nie dotyka uprawnień.
- **Endpoint jest idempotentny w sensie „ponów zaproszenie”** — kolejne wywołanie unieważnia
  poprzedni token i wysyła nowy.

## Stan (2026-07-25) — odłożone

**Blokowane przez [#007](./2026-07-09--007--acl-roles-permissions.md).** UI nadawania uprawnień nie
ma sensu, dopóki backend nie egzekwuje reguł nadawania (zasada podzbioru, bramka na role
ponad-zborowe) — inaczej picker obiecywałby rzeczy, których API i tak nie wykona.

Zrobione: sekcja Ludzie/Służby na stronie edycji zboru z wyborem roli
([#021](./2026-07-09--021--people-services-section-ux.md)), ograniczenie ról ponad-zborowych do
admina w UI (`ChurchPeopleSection.vue:115`). Brak: wyszukiwarka istniejącej osoby (P-7 — endpoint
gotowy, brak wywołania z UI), invite flow, ekran ról dla biskupów, audit log.
