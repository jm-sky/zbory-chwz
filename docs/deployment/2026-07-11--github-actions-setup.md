# GitHub Actions — deploy z brancha `develop`

## Workflow

Plik `.github/workflows/deploy.yml`:

1. **Lint + type-check** na runnerze GitHub (`pnpm lint`, `pnpm type-check`)
2. **Deploy przez SSH** — użytkownik `deploy`, `bash scripts/deploy.sh` w katalogu projektu

**Trigger:** push na `develop` lub ręcznie (`workflow_dispatch`).

## Sekrety GitHub (Settings → Secrets → Actions)

| Secret | Wartość |
|--------|---------|
| `VPS_HOST` | IP lub hostname VPS |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | klucz prywatny `/home/deploy/.ssh/id_ed25519` (cały plik + newline na końcu) |
| `VPS_PROJECT_PATH` | `/home/madeyskij/projects/zbory-chwz` |
| `VPS_PORT` | opcjonalnie `22` |

## Deploy key (git pull na serwerze)

Settings → Deploy keys → Add deploy key (read-only):

```bash
sudo cat /home/deploy/.ssh/id_ed25519_github.pub
```

Bez tego klucza `git pull origin develop` w `deploy.sh` się nie powiedzie.

## Setup serwera (jednorazowo)

```bash
cd /home/madeyskij/projects/zbory-chwz
bash scripts/setup-ci-server.sh
```

Po zmianie grup wyloguj się i zaloguj ponownie (`groups` powinno zawierać `deploy`).

## Weryfikacja

```bash
# jako deploy (z innej sesji / po setupie)
sudo -u deploy bash -lc 'cd /home/madeyskij/projects/zbory-chwz && CI=true bash scripts/deploy.sh'
```

Albo w GitHub: Actions → Deploy to Production → Run workflow.

## Ścieżki produkcyjne

| Cel | Ścieżka |
|-----|---------|
| Repo | `/home/madeyskij/projects/zbory-chwz` |
| Frontend (Caddy) | `/var/www/zbory-chwz` |
| Backend | Docker Compose w `backend/` |
