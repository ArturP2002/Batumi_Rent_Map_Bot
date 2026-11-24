# Runbook — deploy & operations

## Local development

```bash
cp .env.example .env
# set BOT_TOKEN, ADMIN_TELEGRAM_IDS, WEBAPP_URL

docker compose up -d db redis minio minio-init
cd backend && pip install -e ".[dev]" && cd ..

python main.py              # API
python main.py bot          # other terminal
python main.py worker       # other terminal
# or: python main.py all

cd backend && python -m app.scripts.seed --count 100
cd ../miniapp && npm install && npm run dev
```

Health: `GET http://localhost:8000/api/health`

## Production checklist

1. VPS with Docker, DNS A-record, TLS (Caddy/Nginx).
2. Set strong `SESSION_SECRET`, real `BOT_TOKEN`, HTTPS `WEBAPP_URL`.
3. Point Telegram BotFather Web App URL to Mini App origin.
4. `docker compose up -d` (or separate systemd units for api/bot/worker).
5. Nightly `pg_dump` to offsite storage; test restore quarterly.
6. Monitor API 5xx, bot polling errors, MinIO disk, Redis memory.
7. Seed first admin via `ADMIN_TELEGRAM_IDS` then manage realtors in admin Mini App.

## Backups

```bash
docker compose exec db pg_dump -U batumi batumi_rent > backup_$(date +%F).sql
```

Restore:

```bash
cat backup_YYYY-MM-DD.sql | docker compose exec -T db psql -U batumi batumi_rent
```

## Load test markers

```bash
python -m app.scripts.seed --count 10000
# then open Mini App map, pan/zoom, confirm p95 list/markers feel <500ms locally
```

## Incident notes

- Map tiles down: Mini App shows error but list/favorites still work.
- Notification failures: stored in `notification_log.error`; business actions already committed.
- Double-submit moderation: audit log records actor; UI disables after click.
