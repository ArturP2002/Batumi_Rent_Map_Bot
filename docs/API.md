# Batumi Rent Map — API contours

Base URL: `/api`

## Auth

`POST /api/public/auth/session`  
Body: `{ "initData": "<Telegram WebApp initData>" }`  
Returns session token. Send as `Authorization: Bearer <token>` or raw header `X-Telegram-Init-Data`.

## Public

| Method | Path | Notes |
|--------|------|-------|
| GET | `/public/me` | Current user + roles |
| GET | `/public/map/markers` | Bbox + filters, lightweight markers |
| GET | `/public/properties` | Paginated list |
| GET | `/public/properties/{id}` | Detail + photos/features |
| GET | `/public/properties/{id}/calendar` | Availability intervals |
| POST | `/public/favorites/{id}` | Toggle favorite |
| GET | `/public/favorites` | Favorites list |
| POST | `/public/inquiries` | Contact click → inquiry |
| GET | `/public/realtors/{id}` | Public realtor profile |
| POST | `/public/reviews` | After confirmed deal |
| POST | `/public/analytics/events` | Client analytics |

## Bot (realtor)

| Method | Path | Notes |
|--------|------|-------|
| POST | `/bot/properties` | Create listing → moderation |
| GET | `/bot/properties/mine` | Realtor listings |
| PATCH | `/bot/properties/{id}` | Edit (critical → re-moderation) |
| POST | `/bot/properties/{id}/photos` | Multipart, max 10 |
| POST | `/bot/properties/{id}/status` | active/hidden/archived |
| POST | `/bot/properties/{id}/confirm-freshness` | Freshness ping |
| GET/POST | `/bot/properties/{id}/calendar` | Intervals |
| GET | `/bot/inquiries` | Realtor inquiries |
| POST | `/bot/deals` | Start triple confirmation |
| POST | `/bot/deals/{id}/client-decide` | Client approve/reject |
| GET | `/bot/deals/mine` | Realtor deals |

## Admin

Requires role `admin`.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/admin/dashboard` | KPI + attention queue |
| GET/PATCH | `/admin/properties...` | List, detail, moderate, edit |
| GET/POST/DELETE | `/admin/.../calendar` | Manage intervals |
| GET/POST | `/admin/realtors` | Create by Telegram ID |
| POST | `/admin/realtors/{id}/block` | Auto-hide listings |
| GET | `/admin/inquiries` | Filterable |
| GET/POST | `/admin/deals` | Decide as admin side |
| GET/POST | `/admin/reviews...` | Moderate |
| GET | `/admin/stats` | Period KPIs + conversions |
| GET | `/admin/stats/export` | csv \| xlsx |
| GET/PUT | `/admin/settings` | Freshness + districts |

## Deep-links (`startapp`)

`property_<id>`, `realtor_<id>`, `admin`, `admin_listings`, `admin_deals`, `admin_reviews`, `deal_<id>`, `favorites`
