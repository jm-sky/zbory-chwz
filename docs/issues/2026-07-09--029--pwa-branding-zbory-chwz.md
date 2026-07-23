# Issue 029 — Rebranding PWA i resztki Gear Stack → Zbory CHWZ

**Data:** 2026-07-09  
**Status:** `done` (2026-07-09)  
**Commits:** `c90be3c`, `6156e71`  
**Obszar:** PWA manifest, meta, copy w UI

## Prompt (Cursor)

> popraw PWA, podmien gear-stack na wlasciwa nazwe. Potem commit, push  
> popraw inne, commit, push

*(sesja `e40047f9`)*

## Decyzja

Projekt powstał z fork/szablonu gear-stack — użytkownik instalujący PWA widział **obcą nazwę i ikony**. Wszystkie ślady „Gear Stack” w manifeście, tytule zakładki i copy zastąpione **Zbory CHWZ** / domeną `zbory.chwz.waw.pl`.

## Implementacja

- `c90be3c` — `fix(pwa): replace Gear Stack branding with Zbory CHWZ`
- `6156e71` — `fix(branding): replace remaining Gear Stack references with Zbory CHWZ`

## Weryfikacja

- „Dodaj do ekranu początkowego” pokazuje Zbory CHWZ
- Brak „Gear Stack” w `manifest.webmanifest`, `index.html`, kluczowych i18n
