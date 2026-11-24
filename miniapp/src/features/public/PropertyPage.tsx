import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api";
import { AMENITIES, roomLabel } from "@/shared/filters";
import { HeartIcon, StateBox } from "@/shared/ui";
import { ZoomableImage } from "@/shared/ZoomableImage";
import "./PropertyPage.css";

type Photo = { id: number; url: string; thumb_url?: string };
type Detail = {
  id: number; public_code: string; rent_type: string; price_usd: number; rooms: string;
  area_m2?: number; floor?: number; floors_total?: number; sleeping_places?: number;
  district?: string; address?: string; description?: string; lat?: number; lon?: number;
  long_term_availability?: string; photos: Photo[]; features?: Record<string, boolean>;
  primary_realtor_id?: number; realtor_ids: number[]; is_favorite?: boolean;
};
type Interval = { start_date: string; end_date: string; kind: string };
type Realtor = {
  id: number; display_name: string; rating_avg: number; rating_count: number;
  photo_url?: string; telegram_contact?: string; whatsapp?: string; phone?: string;
};
const availability: Record<string, string> = { available: "Свободна", occupied: "Занята", unknown: "Статус уточняется" };
const money = (v: number) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(v);
const dateKey = (year: number, month: number, day: number) => `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
const fmtMonth = (year: number, month: number) => new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(Date.UTC(year, month, 1)));

function CalendarGrid({ intervals }: { intervals: Interval[] }) {
  const now = new Date();
  const [offset, setOffset] = useState(0);
  const first = new Date(now.getFullYear(), now.getMonth() + offset, 1);
  const year = first.getFullYear();
  const month = first.getMonth();
  const count = new Date(year, month + 1, 0).getDate();
  const leading = (first.getDay() + 6) % 7;
  const today = dateKey(now.getFullYear(), now.getMonth(), now.getDate());
  const cells = [...Array.from({ length: leading }, () => ""), ...Array.from({ length: count }, (_, i) => dateKey(year, month, i + 1))];
  const occupied = (day: string) => intervals.some(range => day >= range.start_date && day < range.end_date);
  return (
    <section className="mbp-card mbp-calendar" aria-label="Календарь занятости">
      <div className="mbp-section-head"><div><span className="mbp-overline">ПОСУТОЧНАЯ АРЕНДА</span><h2>Календарь доступности</h2></div></div>
      <div className="mbp-month"><button type="button" onClick={() => setOffset(v => Math.max(0, v - 1))} disabled={offset === 0} aria-label="Предыдущий месяц">‹</button><strong>{fmtMonth(year, month)}</strong><button type="button" onClick={() => setOffset(v => Math.min(11, v + 1))} disabled={offset >= 11} aria-label="Следующий месяц">›</button></div>
      <div className="mbp-calendar-grid mbp-weekdays">{["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map(d => <span key={d}>{d}</span>)}</div>
      <div className="mbp-calendar-grid">{cells.map((day, i) => <span key={`${day}-${i}`} className={["mbp-day", !day ? "is-empty" : "", day && occupied(day) ? "is-occupied" : "", day && day < today ? "is-past" : ""].join(" ")} aria-label={day ? `${day}: ${occupied(day) ? "занято" : "нет отмеченной занятости"}` : undefined}>{day ? Number(day.slice(-2)) : ""}</span>)}</div>
      <div className="mbp-legend"><span><i className="mbp-legend-free" /> Нет отмеченной занятости</span><span><i className="mbp-legend-busy" /> Занято</span></div>
      <p className="mbp-calendar-note">Календарь информационный. Свободные даты уточняйте у риелтора — выбор дат не является бронированием.</p>
    </section>
  );
}

export function PropertyPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<Detail | null>(null);
  const [realtor, setRealtor] = useState<Realtor | null>(null);
  const [calendar, setCalendar] = useState<Interval[]>([]);
  const [photoIdx, setPhotoIdx] = useState(0);
  const [lightbox, setLightbox] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [favBusy, setFavBusy] = useState(false);
  const [contactBusy, setContactBusy] = useState(false);

  useEffect(() => {
    let active = true;
    setData(null); setRealtor(null); setCalendar([]); setError(null); setPhotoIdx(0); setLightbox(false);
    (async () => {
      try {
        const detail = await api<Detail>(`/api/public/properties/${id}`);
        if (!active) return;
        setData(detail);
        const rid = detail.primary_realtor_id || detail.realtor_ids?.[0];
        if (rid) void api<Realtor>(`/api/public/realtors/${rid}`).then(v => { if (active) setRealtor(v); }).catch(() => {});
        if (detail.rent_type === "daily") void api<Interval[]>(`/api/public/properties/${id}/calendar`).then(v => { if (active) setCalendar(v); }).catch(() => { if (active) setNotice("Не удалось обновить календарь. Уточните даты у риелтора."); });
      } catch { if (active) setError("Объявление не найдено или недоступно"); }
    })();
    return () => { active = false; };
  }, [id]);

  useEffect(() => {
    if (!lightbox) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setLightbox(false);
      if (e.key === "ArrowLeft") setPhotoIdx(i => (i - 1 + (data?.photos.length || 1)) % (data?.photos.length || 1));
      if (e.key === "ArrowRight") setPhotoIdx(i => (i + 1) % (data?.photos.length || 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [lightbox, data?.photos.length]);

  async function toggleFavorite() {
    if (!data || favBusy) return;
    setFavBusy(true); setNotice(null);
    try {
      await api(`/api/public/favorites/${data.id}`, { method: "POST" });
      setData(prev => prev ? { ...prev, is_favorite: !prev.is_favorite } : prev);
    } catch { setNotice("Не удалось изменить избранное. Откройте приложение через Telegram."); }
    finally { setFavBusy(false); }
  }

  async function contact(channel: "telegram" | "whatsapp" | "phone") {
    if (!data || !realtor || contactBusy) return;
    setContactBusy(true); setNotice(null);
    try {
      await api("/api/public/inquiries", { method: "POST", body: JSON.stringify({ property_id: data.id, realtor_id: realtor.id, channel }) });
      if (channel === "telegram" && realtor.telegram_contact) {
        const url = `https://t.me/${realtor.telegram_contact.replace(/^@/, "")}`;
        if (window.Telegram?.WebApp?.openTelegramLink) window.Telegram.WebApp.openTelegramLink(url);
        else window.location.href = url;
      } else if (channel === "whatsapp" && realtor.whatsapp) {
        const url = `https://wa.me/${realtor.whatsapp.replace(/\D/g, "")}`;
        if (window.Telegram?.WebApp?.openLink) window.Telegram.WebApp.openLink(url);
        else window.location.href = url;
      } else if (channel === "phone" && realtor.phone) {
        window.location.href = `tel:${realtor.phone}`;
      }
    } catch { setNotice("Не удалось зафиксировать обращение. Проверьте авторизацию Telegram."); }
    finally { setContactBusy(false); }
  }

  if (error) return <div className="page"><StateBox title={error}><Link to="/list" className="btn btn-primary">К списку квартир</Link></StateBox></div>;
  if (!data) return <div className="page"><StateBox title="Загружаем квартиру…" /></div>;
  const photos = data.photos || [];
  const photo = photos[photoIdx];
  const amenities = AMENITIES.filter(a => data.features?.[a.key]);
  const hasMany = photos.length > 1;
  const isDaily = data.rent_type === "daily";
  const mapUrl = data.lat != null && data.lon != null ? `/map?lat=${data.lat}&lon=${data.lon}&id=${data.id}` : "/map";
  const mainChannel = realtor?.telegram_contact ? "telegram" : realtor?.whatsapp ? "whatsapp" : realtor?.phone ? "phone" : null;
  return (
    <div className="page mbp-page">
      <div className="mbp-gallery">
        {photo ? <button type="button" className="mbp-gallery-image" onClick={() => setLightbox(true)} aria-label="Открыть фотографию на весь экран"><img src={photo.url} alt={`Квартира в Батуми, фотография ${photoIdx + 1}`} /></button> : <div className="mbp-no-photo">Фотографии скоро появятся</div>}
        <div className="mbp-gallery-toolbar"><button type="button" onClick={() => navigate(-1)} aria-label="Назад">←</button><button type="button" onClick={() => void toggleFavorite()} disabled={favBusy} aria-label={data.is_favorite ? "Убрать из избранного" : "В избранное"} aria-pressed={Boolean(data.is_favorite)} className={data.is_favorite ? "is-favorite" : ""}><HeartIcon filled={Boolean(data.is_favorite)} /></button></div>
        {hasMany && <><button type="button" className="mbp-photo-arrow prev" onClick={() => setPhotoIdx(v => (v - 1 + photos.length) % photos.length)} aria-label="Предыдущее фото">‹</button><button type="button" className="mbp-photo-arrow next" onClick={() => setPhotoIdx(v => (v + 1) % photos.length)} aria-label="Следующее фото">›</button><div className="mbp-photo-count">{photoIdx + 1} / {photos.length}</div></>}
      </div>
      {hasMany && <div className="mbp-thumbnails" aria-label="Все фотографии">{photos.slice(0, 8).map((p, idx) => <button key={p.id} type="button" onClick={() => setPhotoIdx(idx)} className={idx === photoIdx ? "active" : ""} aria-label={`Фото ${idx + 1}`}><img src={p.thumb_url || p.url} alt="" loading="lazy" /></button>)}</div>}
      <main className="mbp-content">
        <div className="mbp-meta"><span>{isDaily ? "ПОСУТОЧНАЯ АРЕНДА" : "ДОЛГОСРОЧНАЯ АРЕНДА"}</span><span>№ {data.public_code}</span></div>
        <div className="mbp-heading"><div><h1>${money(Number(data.price_usd))}<small>{isDaily ? " / сутки" : " / месяц"}</small></h1><p>{data.district || data.address || "Батуми"}</p></div>{!isDaily && <span className="mbp-availability">{availability[data.long_term_availability || "unknown"] || "Статус уточняется"}</span>}</div>
        <div className="mbp-specs"><div><span>⌂</span><strong>{roomLabel(data.rooms)}</strong><small>комнаты</small></div><div><span>◱</span><strong>{data.area_m2 ?? "—"} м²</strong><small>площадь</small></div><div><span>↟</span><strong>{data.floor ?? "—"}/{data.floors_total ?? "—"}</strong><small>этаж</small></div><div><span>♧</span><strong>{data.sleeping_places ?? "—"}</strong><small>спальных мест</small></div></div>
        <section className="mbp-card"><div className="mbp-section-head"><div><span className="mbp-overline">ОБ ОБЪЕКТЕ</span><h2>Описание квартиры</h2></div></div><p className="mbp-description">{data.description || "Описание пока не добавлено."}</p><Link className="mbp-inline-link" to={mapUrl}>⌖ Посмотреть на карте <span>↗</span></Link></section>
        {amenities.length > 0 && <section className="mbp-card"><div className="mbp-section-head"><div><span className="mbp-overline">ВСЁ ДЛЯ КОМФОРТА</span><h2>Удобства</h2></div><span className="mbp-count">{amenities.length}</span></div><div className="mbp-amenities">{amenities.map(a => <span key={a.key}><i>✓</i>{a.label}</span>)}</div></section>}
        {isDaily && <CalendarGrid intervals={calendar} />}
        {realtor && <section className="mbp-card mbp-realtor"><div className="mbp-section-head"><div><span className="mbp-overline">ВАШ КОНТАКТ</span><h2>Риелтор</h2></div></div><div className="mbp-realtor-row">{realtor.photo_url ? <img src={realtor.photo_url} alt="" /> : <span className="mbp-avatar">{realtor.display_name.slice(0,1).toUpperCase()}</span>}<div><strong>{realtor.display_name}</strong><small>{realtor.rating_count > 0 ? `★ ${Number(realtor.rating_avg).toFixed(1)} · ${realtor.rating_count} оценок` : "Пока нет отзывов"}</small></div><Link to={`/realtor/${realtor.id}`} aria-label="Открыть профиль риелтора">↗</Link></div></section>}
        {notice && <p className="mbp-notice" role="alert">{notice}</p>}
        <div className="mbp-scroll-end" aria-hidden="true" />
      </main>
      <footer className="mbp-contact-bar"><div className="mbp-contact-price"><strong>${money(Number(data.price_usd))}</strong><span>{isDaily ? "за сутки" : "в месяц"}</span></div><div className="mbp-contact-buttons">{mainChannel && <button type="button" className="mbp-contact-primary" disabled={contactBusy} onClick={() => void contact(mainChannel)}>{contactBusy ? "Открываем…" : mainChannel === "phone" ? "Позвонить" : "Написать"}</button>}{realtor?.whatsapp && mainChannel !== "whatsapp" && <button type="button" className="mbp-contact-secondary" disabled={contactBusy} onClick={() => void contact("whatsapp")}>WA</button>}{realtor?.phone && mainChannel !== "phone" && <button type="button" className="mbp-contact-secondary" disabled={contactBusy} onClick={() => void contact("phone")} aria-label="Позвонить">☎</button>}</div></footer>
      {lightbox && photo && <div className="lightbox" role="dialog" aria-modal="true" aria-label="Фотогалерея"><div className="lightbox-top"><span className="gallery-counter">{photoIdx + 1}/{photos.length}</span><button type="button" className="lightbox-close" aria-label="Закрыть" onClick={() => setLightbox(false)}>×</button></div><div className="lightbox-stage">{hasMany && <button type="button" className="gallery-nav gallery-nav--prev" onClick={() => setPhotoIdx(v => (v - 1 + photos.length) % photos.length)} aria-label="Предыдущее фото">‹</button>}<ZoomableImage src={photo.url} resetKey={`${photo.id}-${photoIdx}`} onSwipeDown={() => setLightbox(false)} />{hasMany && <button type="button" className="gallery-nav gallery-nav--next" onClick={() => setPhotoIdx(v => (v + 1) % photos.length)} aria-label="Следующее фото">›</button>}</div></div>}
    </div>
  );
}
