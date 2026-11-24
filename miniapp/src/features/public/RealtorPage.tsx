import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api";
import { roomLabel } from "@/shared/filters";
import "./CommunityPages.css";

type Listing = {id: number; cover_url?: string | null; price_usd: number; rent_type: string; rooms: string; area_m2?: number | null; district?: string | null; address?: string | null};
type Review = {id: number; rating: number; text?: string | null; created_at?: string | null; author_name?: string | null};
type Realtor = {id: number; display_name: string; photo_url?: string | null; bio?: string | null; rating_avg: number; rating_count: number; active_listings: number; reviews?: Review[]; properties?: Listing[]};
const money = (v: number) => Number(v).toLocaleString("en-US", {maximumFractionDigits: 0});

export function RealtorPage() {
  const {id} = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<Realtor | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { let live = true; setData(null); setError(null); api<Realtor>(`/api/public/realtors/${id}`).then(x => {if (live) setData(x);}).catch(() => {if (live) setError("Профиль риелтора сейчас недоступен.");}); return () => {live = false;}; }, [id]);

  return <div className="page mbc-page"><header className="mbc-top"><button className="mbc-back" onClick={() => navigate(-1)} aria-label="Назад">←</button><span className="mbc-brand">batumi <strong>rent.</strong></span><Link to="/map" className="mbc-header-link">Карта ↗</Link></header>
    {error ? <div className="mbc-alert" role="alert">{error}<div><Link to="/list" className="mbc-primary">К квартирам</Link></div></div> : !data ? <div className="mbc-skeleton"><div/><div/></div> : <>
      <section className="mbc-profile"><div className="mbc-overline">ПРОВЕРЕННЫЕ КОНТАКТЫ</div><div className="mbc-profile-row">{data.photo_url ? <img src={data.photo_url} alt="" className="mbc-avatar"/> : <div className="mbc-avatar mbc-initial">{data.display_name?.slice(0,1).toUpperCase() || "Р"}</div>}<div><h1>{data.display_name}</h1><p>Риелтор · Батуми</p></div></div><div className="mbc-stats"><div><strong>{data.rating_count ? Number(data.rating_avg).toFixed(1) : "—"}<span className="mbc-star">★</span></strong><small>Средняя оценка</small></div><div><strong>{data.rating_count ?? 0}</strong><small>Отзывов</small></div><div><strong>{data.active_listings ?? data.properties?.length ?? 0}</strong><small>Объявлений</small></div></div>{data.bio && <p className="mbc-bio">{data.bio}</p>}</section>
      <section className="mbc-section"><div className="mbc-section-title"><div><span className="mbc-overline">ОПЫТ КЛИЕНТОВ</span><h2>Отзывы об агенте</h2></div><span>{data.reviews?.length || 0}</span></div>{data.reviews?.length ? <div className="mbc-reviews">{data.reviews.map(r => <article className="mbc-review" key={r.id}><div className="mbc-review-top"><strong>{r.author_name || "Клиент"}</strong><span aria-label={`Оценка: ${r.rating} из 5`}>{"★".repeat(Math.max(0, Math.min(5, r.rating)))}</span></div>{r.text && <p>{r.text}</p>}<small>Отзыв после подтверждённой аренды</small></article>)}</div> : <div className="mbc-empty mbc-small"><h3>Пока нет отзывов</h3><p>Здесь появятся отзывы клиентов после подтверждённой аренды и модерации.</p></div>}</section>
      <section className="mbc-section"><div className="mbc-section-title"><div><span className="mbc-overline">ПРЕДЛОЖЕНИЯ</span><h2>Квартиры риелтора</h2></div><span>{data.properties?.length || 0}</span></div>{data.properties?.length ? <div className="mbc-grid">{data.properties.map(item => <article className="mbc-property" key={item.id}><button className="mbc-property-image" aria-label="Открыть квартиру" onClick={() => navigate(`/property/${item.id}`)}>{item.cover_url ? <img src={item.cover_url} alt="Квартира" loading="lazy"/> : <span className="mbc-photo-empty">Нет фото</span>}</button><span className="mbc-rent-badge">{item.rent_type === "daily" ? "Посуточно" : "Долгосрочно"}</span><button className="mbc-property-info" onClick={() => navigate(`/property/${item.id}`)}><strong>${money(item.price_usd)} <small>{item.rent_type === "daily" ? "/ сутки" : "/ месяц"}</small></strong><span>{roomLabel(item.rooms)} · {item.area_m2 != null ? `${item.area_m2} м²` : "Площадь уточняется"}</span><span className="mbc-location">⌖ {item.district || item.address || "Батуми"}</span><span className="mbc-details">Открыть объявление ↗</span></button></article>)}</div> : <div className="mbc-empty mbc-small"><p>У риелтора пока нет активных предложений.</p></div>}</section>
    </>}
  </div>;
}
