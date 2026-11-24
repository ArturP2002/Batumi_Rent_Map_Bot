import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/shared/api";
import { roomLabel } from "@/shared/filters";
import { HeartIcon } from "@/shared/ui";
import "./CommunityPages.css";

type Card = { id: number; cover_url?: string | null; price_usd: number; rooms: string; area_m2?: number | null; district?: string | null; address?: string | null; is_favorite?: boolean; rent_type: string };
const money = (n: number) => Number(n).toLocaleString("en-US", {maximumFractionDigits: 0});

export function FavoritesPage() {
  const [items, setItems] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<number[]>([]);
  const navigate = useNavigate();

  useEffect(() => { let live = true; api<Card[]>("/api/public/favorites").then(result => { if (live) setItems(result); }).catch(() => { if (live) setError("Не удалось открыть избранное. Запустите приложение внутри Telegram."); }).finally(() => { if (live) setLoading(false); }); return () => {live = false;}; }, []);

  async function remove(id: number) {
    if (pending.includes(id)) return;
    setPending(p => [...p, id]);
    setError(null);
    try { await api(`/api/public/favorites/${id}`, {method: "POST"}); setItems(p => p.filter(item => item.id !== id)); }
    catch { setError("Не удалось удалить квартиру из избранного. Попробуйте ещё раз."); }
    finally { setPending(p => p.filter(n => n !== id)); }
  }

  return <div className="page mbc-page">
    <header className="mbc-top"><Link to="/map" className="mbc-back" aria-label="Назад к карте">←</Link><span className="mbc-brand">batumi <strong>rent.</strong></span><Link to="/list" className="mbc-header-link">Каталог ↗</Link></header>
    <div className="mbc-heading"><div className="mbc-overline">ВАША КОЛЛЕКЦИЯ</div><h1>Избранные <em>квартиры.</em></h1><p>Место для вариантов, к которым хочется вернуться.</p></div>
    {!loading && !error && items.length > 0 && <div className="mbc-count">Сохранено: {items.length}</div>}
    {error && <div className="mbc-alert" role="alert">{error}</div>}
    {loading ? <div className="mbc-skeleton" aria-label="Загружаем избранное"><div/><div/></div> : !error && !items.length ?
      <div className="mbc-empty"><span aria-hidden>♡</span><h2>Пока ничего не сохранено</h2><p>Отмечайте понравившиеся квартиры сердечком, чтобы сравнить их позже.</p><Link to="/list" className="mbc-primary">Смотреть квартиры <span>↗</span></Link></div> :
      <div className="mbc-grid">{items.map(item => <article key={item.id} className="mbc-property">
        <button className="mbc-property-image" onClick={() => navigate(`/property/${item.id}`)} aria-label="Открыть квартиру">{item.cover_url ? <img src={item.cover_url} alt={`Квартира — ${item.district || "Батуми"}`} loading="lazy"/> : <span className="mbc-photo-empty">Фото пока нет</span>}</button>
        <span className="mbc-rent-badge">{item.rent_type === "daily" ? "Посуточно" : "Долгосрочно"}</span>
        <button type="button" className="mbc-fav" disabled={pending.includes(item.id)} onClick={() => void remove(item.id)} aria-label="Убрать из избранного"><HeartIcon filled /></button>
        <button className="mbc-property-info" onClick={() => navigate(`/property/${item.id}`)}><strong>${money(item.price_usd)} <small>{item.rent_type === "daily" ? "/ сутки" : "/ месяц"}</small></strong><span>{roomLabel(item.rooms)} · {item.area_m2 != null ? `${item.area_m2} м²` : "Площадь уточняется"}</span><span className="mbc-location">⌖ {item.district || item.address || "Батуми"}</span><span className="mbc-details">Подробнее о квартире ↗</span></button>
      </article>)}</div>}
    <Link className="mbc-map-link" to="/map">⌖ Вернуться на карту</Link>
  </div>;
}
