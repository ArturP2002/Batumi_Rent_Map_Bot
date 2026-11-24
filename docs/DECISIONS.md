# Batumi Rent Map — Design Decisions

## Scope

- Full TZ v1.1 delivery in phases 0–6.
- Realtor management **only via Telegram bot** — no realtor Mini App cabinet.
- Public Mini App + closed admin section in the same Mini App.
- No online payments, auto-booking, in-app chat, external web cabinets, multilanguage.

## Data model

| Decision | Choice |
|----------|--------|
| Realtors per property | Many-to-many via `property_realtors`; inquiry/deal binds a specific realtor |
| Photos per listing | Max **10**, JPEG/PNG/WebP, ≤5 MB each; S3 + previews |
| Rooms filter | studio, 1, 2, 3, 4+ |
| Price | USD; per day or per month by `rent_type` |
| Amenities | Exactly 18 boolean features from TZ |
| Availability intervals | Half-open `[start, end)` in `Asia/Tbilisi` |
| Deal proof | Triple confirmation (realtor + client + admin); no documents required |
| Long-term availability | Status flag; calendar optional |
| PII export | Admin role only, audited |

## Freshness defaults

Configurable in `system_settings`:

- Confirm every **14** days
- Reminder after **3** days without reply
- Hide after **4** more days without reply

## Stack

- Mini App: React + TypeScript + Vite + Telegram Mini Apps SDK
- Map: MapLibre GL JS + OpenFreeMap (swappable basemap)
- Backend: Python FastAPI
- Bot: aiogram 3
- DB: PostgreSQL + PostGIS
- Cache/jobs: Redis
- Photos: S3-compatible (MinIO locally)

## UI

Reference screenshots are aspirational. Match brand feel (blue/white, map-first) without pixel-perfect clone. Admin UI is mobile-first card lists inside Telegram viewport.
