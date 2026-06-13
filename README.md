# poke-chaser-django

Django backend for Poke Chase, running in Docker Compose with PostgreSQL, Redis, and MailHog.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Quick start

### 1. Environment variables

```bash
cp .env.example .env
```

### 2. First-time setup

```bash
./bin/setup
```

This builds images, runs migrations, and prompts you to create a superuser. Migrations are not run automatically on `./bin/start` — use `./bin/setup` or `./bin/migrate` when needed.

### 3. Start all services

```bash
./bin/start
```

- Django: http://localhost:8000
- MailHog UI: http://localhost:8025

Verify services are running:

```bash
docker compose ps
```

## Project structure

```
poke-chaser-django/
├── bin/                 # Dev helper scripts
├── pokechaser/          # Django project settings
├── manage.py
├── Dockerfile
├── docker-entrypoint.sh # Container entrypoint (passes commands through)
├── requirements.txt
├── docker-compose.yml   # Postgres, Redis, MailHog, Django
├── .env.example         # Committed env template
└── .env                 # Local secrets (not committed)
```

## bin/ scripts

| Script | Purpose |
|--------|---------|
| `./bin/setup` | First-time setup: build, migrate, createsuperuser |
| `./bin/start` | Start all services (`docker compose up`) |
| `./bin/build` | Build Docker images |
| `./bin/migrate` | Run Django migrations |
| `./bin/rebuild` | Rebuild images and run migrations |
| `./bin/bash` | Open a shell in the app container |

## Common commands

```bash
# First time
./bin/setup

# Daily dev
./bin/start

# After model changes
./bin/migrate

# After Dockerfile or requirements changes
./bin/rebuild

# Shell into app container
./bin/bash

# View Django logs (when running in background)
docker compose logs -f app

# Stop services
docker compose down

# Stop and remove persisted Postgres data
docker compose down -v
```

## Optional: host-only Django dev

Run supporting services in Docker but Django on your Mac (useful for faster debugging without rebuilding):

```bash
docker compose up postgres redis mailhog -d
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
POSTGRES_HOST=localhost EMAIL_HOST=localhost python manage.py migrate
POSTGRES_HOST=localhost EMAIL_HOST=localhost python manage.py runserver
```

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_DB` | Database name | `poke_chaser` |
| `POSTGRES_USER` | Database user | `poke_chaser` |
| `POSTGRES_PASSWORD` | Database password | — |
| `POSTGRES_HOST` | DB host (`postgres` in Compose, `localhost` on host) | `postgres` |
| `POSTGRES_PORT` | Database port | `5432` |
| `REDIS_HOST` | Redis host | `redis` |
| `REDIS_PORT` | Redis port | `6379` |
| `EMAIL_HOST` | MailHog SMTP host | `mailhog` |
| `EMAIL_PORT` | MailHog SMTP port | `1025` |
| `DJANGO_SECRET_KEY` | Django secret key | — |
| `DJANGO_DEBUG` | Enable debug mode | `True` |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed hosts | `localhost,127.0.0.1,app` |

## SFTP service

The `sftp` service in `docker-compose.yml` is commented out by default. Uncomment it once a `./sftp` build context is set up.
