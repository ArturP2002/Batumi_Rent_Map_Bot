# Batumi Rent Map

Telegram-бот + Mini App для поиска и аренды квартир в Батуми (ТЗ v1.1).

- Публичный Mini App: карта, фильтры, список, карточки, календарь, избранное, профили, отзывы
- Telegram-бот риелтора (без кабинета в Mini App)
- Админ-раздел внутри того же Mini App
- Backend: FastAPI + PostgreSQL/PostGIS + Redis + S3/MinIO + aiogram

## Docs

- [Architecture map](docs/ARCHITECTURE.md)
- [Decisions](docs/DECISIONS.md)
- [API](docs/API.md)
- [Runbook](docs/RUNBOOK.md)
- [Admin guide](docs/ADMIN_GUIDE.md)
- [Realtor guide](docs/REALTOR_GUIDE.md)

## Quick start

```bash
cp .env.example .env
# заполните BOT_TOKEN, ADMIN_TELEGRAM_IDS, WEBAPP_URL

docker compose up -d db redis minio minio-init

cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cd ..

# из корня проекта (main.py сам переключится на backend/.venv)
python3 main.py             # API
python3 main.py bot         # Telegram-бот
python3 main.py worker      # фоновые задачи
python3 main.py all         # API + bot + worker

# Mini App
cd miniapp && npm install && npm run dev
```

Seed demo data:

```bash
cd backend && python -m app.scripts.seed --count 100
# rich dataset for admin/stats/reviews UI (safe wipe of previous rich seed):
cd backend && ENV_FILE=../.env PYTHONPATH=. python -m app.scripts.seed_rich --wipe-demo
```

## Acceptance highlights (§16)

- Map markers + clusters via MapLibre; filters sync map↔list
- Daily calendar managed by realtor bot + admin Mini App
- Realtor full listing lifecycle via bot only
- Admin dashboard, moderation, realtors, deals, reviews, stats export
- Triple confirmation before review; rating from published reviews only
- Server-side role checks on admin/realtor APIs
