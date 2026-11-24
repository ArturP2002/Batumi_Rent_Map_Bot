import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api";
import { AMENITIES, roomLabel } from "@/shared/filters";
import { HeartIcon, StateBox } from "@/shared/ui";
import { ZoomableImage } from "@/shared/ZoomableImage";

type Detail = {
  id: number;
  public_code: string;
  rent_type: string;
  price_usd: number;
  rooms: string;
  area_m2?: number;
  floor?: number;
  floors_total?: number;
  sleeping_places?: number;
  district?: string;
  address?: string;
  description?: string;
  lat?: number;
  lon?: number;
  long_term_availability?: string;
  photos: { id: number; url: string; thumb_url?: string }[];
  features?: Record<string, boolean>;
  primary_realtor_id?: number;
  realtor_ids: number[];
  is_favorite?: boolean;
};

const LONG_TERM_RU: Record<string, string> = {
  available: "Свободна",
  occupied: "Занята",
  unknown: "Статус неизвестен",
};

type Interval = { start_date: string; end_date: string; kind: string };
type Realtor = {
  id: number;
  display_name: string;
  rating_avg: number;
  rating_count: number;
  photo_url?: string;
  telegram_contact?: string;
  whatsapp?: string;
  phone?: string;
};

export function PropertyPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<Detail | null>(null);
  const [realtor, setRealtor] = useState<Realtor | null>(null);
  const [calendar, setCalendar] = useState<Interval[]>([]);
  const [photoIdx, setPhotoIdx] = useState(0);
  const [lightbox, setLightbox] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setPhotoIdx(0);
    setLightbox(false);
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(false);
      if (e.key === "ArrowLeft") stepPhoto(-1);
      if (e.key === "ArrowRight") stepPhoto(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lightbox, data?.photos.length]);

  async function load() {
    try {
      const detail = await api<Detail>(`/api/public/properties/${id}`);
      setData(detail);
      if (detail.rent_type === "daily") {
        setCalendar(await api<Interval[]>(`/api/public/properties/${id}/calendar`));
      }
      const rid = detail.primary_realtor_id || detail.realtor_ids[0];
      if (rid) setRealtor(await api<Realtor>(`/api/public/realtors/${rid}`));
    } catch {
      setError("Объявление не найдено");
    }
  }

  async function toggleFavorite() {
    if (!data) return;
    try {
      await api(`/api/public/favorites/${data.id}`, { method: "POST" });
      await load();
    } catch {
      setError("Войдите через Telegram, чтобы сохранить в избранное");
    }
  }

  async function contact(channel: "telegram" | "whatsapp" | "phone") {
    if (!data || !realtor) return;
    try {
      await api("/api/public/inquiries", {
        method: "POST",
        body: JSON.stringify({
          property_id: data.id,
          realtor_id: realtor.id,
          channel,
        }),
      });
    } catch {
      setError("Не удалось зафиксировать обращение. Проверьте авторизацию Telegram.");
      return;
    }
    if (channel === "telegram" && realtor.telegram_contact) {
      const u = realtor.telegram_contact.replace("@", "");
      window.Telegram?.WebApp?.openTelegramLink(`https://t.me/${u}`);
    } else if (channel === "whatsapp" && realtor.whatsapp) {
      window.Telegram?.WebApp?.openLink(
        `https://wa.me/${realtor.whatsapp.replace(/\D/g, "")}`,
      );
    } else if (channel === "phone" && realtor.phone) {
      window.Telegram?.WebApp?.openLink(`tel:${realtor.phone}`);
    }
  }

  function stepPhoto(delta: number) {
    const total = data?.photos.length || 0;
    if (total < 2) return;
    setPhotoIdx((i) => (i + delta + total) % total);
  }

  if (error) return <StateBox title={error} />;
  if (!data) return <StateBox title="Загрузка…" />;

  const photos = data.photos;
  const photo = photos[photoIdx];
  const hasMany = photos.length > 1;
  const period = data.rent_type === "daily" ? "/сутки" : "/мес";
  const activeAmenities = AMENITIES.filter((a) => data.features?.[a.key]);

  return (
    <div className="page">
      <div className="property-hero">
        {photo ? (
          <button
            type="button"
            className="property-hero-media"
            onClick={() => setLightbox(true)}
            aria-label="Открыть фото"
          >
            <img src={photo.url} alt="" />
          </button>
        ) : (
          <div className="card state-box" style={{ borderRadius: 0, minHeight: 220 }}>
            Нет фото
          </div>
        )}
        <div className="property-hero-bar">
          <button type="button" className="chip btn-ghost" onClick={() => navigate(-1)}>
            ← Назад
          </button>
          <button
            type="button"
            className={`chip chip-fav btn-ghost ${data.is_favorite ? "is-on" : ""}`}
            aria-label={data.is_favorite ? "Убрать из избранного" : "В избранное"}
            aria-pressed={Boolean(data.is_favorite)}
            onClick={() => void toggleFavorite()}
          >
            <HeartIcon filled={Boolean(data.is_favorite)} />
          </button>
        </div>
        {photo && (
          <div className="property-hero-controls">
            {hasMany && (
              <button
                type="button"
                className="gallery-nav gallery-nav--prev"
                aria-label="Предыдущее фото"
                onClick={(e) => {
                  e.stopPropagation();
                  stepPhoto(-1);
                }}
              >
                ‹
              </button>
            )}
            <div className="property-hero-meta">
              <span className="gallery-counter">
                {photoIdx + 1}/{photos.length}
              </span>
            </div>
            {hasMany && (
              <button
                type="button"
                className="gallery-nav gallery-nav--next"
                aria-label="Следующее фото"
                onClick={(e) => {
                  e.stopPropagation();
                  stepPhoto(1);
                }}
              >
                ›
              </button>
            )}
          </div>
        )}
        {hasMany && (
          <div className="gallery-dots" role="tablist" aria-label="Фотографии">
            {photos.map((p, i) => (
              <button
                key={p.id}
                type="button"
                role="tab"
                aria-selected={i === photoIdx}
                className={`gallery-dot ${i === photoIdx ? "is-active" : ""}`}
                aria-label={`Фото ${i + 1}`}
                onClick={() => setPhotoIdx(i)}
              />
            ))}
          </div>
        )}
      </div>

      <div className="muted" style={{ marginBottom: 4 }}>
        {data.public_code}
      </div>
      <h1 className="property-price">
        ${data.price_usd}
        <span className="muted" style={{ fontFamily: "var(--font-ui)", fontSize: "1rem" }}>
          {" "}
          {period}
        </span>
      </h1>
      <div className="muted">
        {roomLabel(data.rooms)} · {data.area_m2 || "—"} м² · {data.district || data.address || "Батуми"}
      </div>
      <div className="muted" style={{ marginBottom: 12 }}>
        Этаж {data.floor || "—"}/{data.floors_total || "—"} · спальных мест {data.sleeping_places || "—"}
      </div>
      {data.rent_type === "long_term" && (
        <div className="badge" style={{ marginBottom: 12 }}>
          {LONG_TERM_RU[data.long_term_availability || "unknown"] || "Статус неизвестен"}
        </div>
      )}

      <div className="stack" style={{ marginBottom: 16 }}>
        {realtor?.telegram_contact && (
          <button type="button" className="btn btn-primary btn-block" onClick={() => void contact("telegram")}>
            Написать риелтору
          </button>
        )}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <Link
            className="btn btn-secondary btn-block"
            to={
              data.lat != null && data.lon != null
                ? `/map?lat=${data.lat}&lon=${data.lon}&id=${data.id}`
                : "/map"
            }
          >
            На карте
          </Link>
          {realtor ? (
            <Link className="btn btn-secondary btn-block" to={`/realtor/${realtor.id}`}>
              Профиль
            </Link>
          ) : (
            <button type="button" className="btn btn-secondary btn-block" disabled>
              Профиль
            </button>
          )}
        </div>
        {realtor?.whatsapp && (
          <button type="button" className="btn btn-secondary btn-block" onClick={() => void contact("whatsapp")}>
            WhatsApp
          </button>
        )}
        {realtor?.phone && (
          <button type="button" className="btn btn-secondary btn-block" onClick={() => void contact("phone")}>
            Позвонить
          </button>
        )}
      </div>

      {realtor && (
        <div className="card" style={{ marginBottom: 12 }}>
          <strong>{realtor.display_name}</strong>
          <div className="muted">
            Рейтинг {realtor.rating_avg} · {realtor.rating_count} отзывов
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: 12 }}>
        <p style={{ marginTop: 0 }}>{data.description || "Без описания"}</p>
        <div className="amenity-grid">
          {activeAmenities.map((a) => (
            <span key={a.key} className="badge">
              {a.label}
            </span>
          ))}
        </div>
      </div>

      {data.rent_type === "daily" && (
        <div className="card" style={{ marginBottom: 12 }}>
          <strong>Календарь занятости</strong>
          <div className="muted">Интервалы [заезд, выезд). Выбор дат не бронирует.</div>
          {!calendar.length && <div className="muted">Свободно / нет блокировок</div>}
          {calendar.map((c, i) => (
            <div key={i} className="muted">
              {c.start_date} → {c.end_date} ({c.kind})
            </div>
          ))}
        </div>
      )}

      {lightbox && photo && (
        <div
          className="lightbox"
          role="dialog"
          aria-modal="true"
          aria-label="Просмотр фото"
        >
          <div className="lightbox-top">
            <span className="gallery-counter">
              {photoIdx + 1}/{photos.length}
            </span>
            <button
              type="button"
              className="lightbox-close"
              aria-label="Закрыть"
              onClick={() => setLightbox(false)}
            >
              ×
            </button>
          </div>
          <div className="lightbox-stage">
            {hasMany && (
              <button
                type="button"
                className="gallery-nav gallery-nav--prev"
                aria-label="Предыдущее фото"
                onClick={() => stepPhoto(-1)}
              >
                ‹
              </button>
            )}
            <ZoomableImage
              src={photo.url}
              resetKey={`${photo.id}-${photoIdx}`}
              onSwipeDown={() => setLightbox(false)}
            />
            {hasMany && (
              <button
                type="button"
                className="gallery-nav gallery-nav--next"
                aria-label="Следующее фото"
                onClick={() => stepPhoto(1)}
              >
                ›
              </button>
            )}
          </div>
          {hasMany && (
            <div className="gallery-dots lightbox-dots">
              {photos.map((p, i) => (
                <button
                  key={p.id}
                  type="button"
                  className={`gallery-dot ${i === photoIdx ? "is-active" : ""}`}
                  aria-label={`Фото ${i + 1}`}
                  onClick={() => setPhotoIdx(i)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
