# Batumi Rent Map — Architecture Map

Navigator for agents and developers. Source of truth for module layout, statuses, and deep-links.

## Repository layout

```
Batumi_Rent_Map_Bot/
├── docs/                 # TZ, architecture, API, runbooks
├── backend/
│   ├── app/
│   │   ├── api/          # public / admin / bot HTTP routes
│   │   ├── bot/          # aiogram handlers, FSM, keyboards
│   │   ├── core/         # config, security (initData), deps
│   │   ├── db/           # SQLAlchemy models, Alembic
│   │   ├── services/     # domain logic
│   │   ├── tasks/        # freshness, aggregates, notifications
│   │   └── storage/      # S3 upload/preview
│   └── tests/
├── miniapp/              # React Mini App (public + admin)
├── docker-compose.yml
└── README.md
```

## System diagram

```
Telegram User/Realtor/Admin
        │
        ├─► aiogram Bot ──► domain services ──► PostgreSQL/PostGIS
        │                          │
        └─► Mini App (React) ──► FastAPI API ──┤
                                               ├─► Redis
                                               └─► S3 (photos)
Background jobs (freshness, aggregates, notify) use Redis + DB + Bot API.
```

## Roles

| Role | Bot | Mini App |
|------|-----|----------|
| Tenant | start, menu, deal/review notifications | map, filters, list, card, calendar, favorites, realtor profile, review |
| Realtor | listing FSM, calendar, inquiries, deals, profile | public profile only |
| Admin | notifications + deep-link to admin, critical fallbacks | dashboard, moderation, realtors, deals, reviews, stats, settings |

One Telegram ID may hold multiple roles. Server re-checks role on every privileged request.

## Status matrices

### Property

`draft` → `moderation` → `active` | `needs_fix` | `hidden` | `blocked` | `archived`

Critical edits (address, photos, core features) may return an active listing to `moderation`.

### Inquiry

`new` → `in_progress` → `failed` | `awaiting_confirmations` → `confirmed` | `rejected`

### Deal confirmations

Three sides: `realtor`, `client`, `admin`. Deal is `confirmed` only when all three approve.

### Review

`pending_moderation` → `published` | `rejected` | `hidden`

One review per confirmed deal. Rating = avg of **published** scores, 1 decimal.

## Domain entities

- `users`, `user_roles`
- `realtor_profiles`
- `properties`, `property_realtors`, `property_photos`, `property_features`
- `availability_intervals`
- `favorites`, `inquiries`, `rental_deals`, `deal_confirmations`
- `reviews`
- `analytics_events`, `daily_aggregates`
- `moderation_history`, `audit_log`, `notification_log`, `system_settings`

## API contours

| Prefix | Audience |
|--------|----------|
| `/api/public/*` | Mini App tenant flows |
| `/api/admin/*` | Admin Mini App (role=admin) |
| `/api/bot/*` | Bot-backed operations (internal token or bot context) |
| `/api/health` | Liveness |

Auth: validate Telegram `initData` (HMAC + TTL), issue short-lived session. Never trust client-supplied Telegram ID alone.

## Mini App deep-links (`startapp`)

| Param | Effect |
|-------|--------|
| `property_<id>` | Open property card |
| `realtor_<id>` | Open realtor profile |
| `admin` | Open admin dashboard (admin only) |
| `admin_listings` | Admin listings queue |
| `admin_deals` | Admin deals queue |
| `admin_reviews` | Admin reviews queue |
| `deal_<id>` | Open client deal confirmation screen (`/deal/:id`) |
| `favorites` | Favorites screen |

Bot WebApp buttons encode these as `startapp` query values.

## Map & geo

- Center: Batumi (~41.6168, 41.6367), zoom ~13
- Backend returns markers in visible bbox (+padding); server-side filters
- Cluster on client; do not send full photos/descriptions with markers
- Debounce pan/zoom; abort stale requests
- Basemap: OpenFreeMap; swappable without rewriting marker logic

## Background jobs

1. Freshness: request confirm → remind → hide (settings-driven)
2. Daily analytics aggregates
3. Notification dispatch with idempotency keys in `notification_log`

## Extension hooks (future paid realtor features)

`realtor_profiles` and `user_roles` leave room for subscription flags; billing is out of v1 scope.
