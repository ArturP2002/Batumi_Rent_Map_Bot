import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, filtersToParams } from "@/shared/api";
import { ROOM_OPTIONS, roomLabel, useFilters } from "@/shared/filters";
import { HeartIcon } from "@/shared/ui";
import { FiltersSheet } from "./FiltersSheet";
import "./ListPage.css";

type Card = {
  id: number;
  cover_url?: string | null;
  price_usd: number;
  rooms: string;
  area_m2?: number | null;
  district?: string | null;
  address?: string | null;
  is_favorite?: boolean;
  rent_type: string;
};

const PAGE_SIZE = 30;
const money = (value: number) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
const roomName = (room: string) => room === "studio" ? "Студия" : ROOM_OPTIONS.includes(room as (typeof ROOM_OPTIONS)[number]) ? `${roomLabel(room)} комн.` : roomLabel(room);

function ListingCard({ item, onOpen, onFavorite, pending }: {
  item: Card;
  onOpen: () => void;
  onFavorite: () => void;
  pending: boolean;
}) {
  return (
    <article className="mbl-card">
      <div className="mbl-photo-wrap">
        <button type="button" className="mbl-photo-action" onClick={onOpen} aria-label={`Открыть квартиру за ${item.price_usd} долларов`}>
          {item.cover_url ? <img src={item.cover_url} alt={`Квартира, ${item.district || "Батуми"}`} loading="lazy" /> :
            <div className="mbl-image-empty" aria-hidden="true"><span>⌂</span><small>Фотография пока недоступна</small></div>}
        </button>
        <span className="mbl-rent-label">{item.rent_type === "daily" ? "Посуточно" : "Долгосрочно"}</span>
        <button type="button" className={`mbl-heart ${item.is_favorite ? "is-selected" : ""}`} onClick={onFavorite}
          disabled={pending} aria-pressed={Boolean(item.is_favorite)} aria-label={item.is_favorite ? "Убрать из избранного" : "В избранное"}>
          <HeartIcon filled={Boolean(item.is_favorite)} />
        </button>
      </div>
      <button type="button" className="mbl-card-info" onClick={onOpen}>
        <span className="mbl-price">${money(Number(item.price_usd))} <small>{item.rent_type === "daily" ? "/ сутки" : "/ месяц"}</small></span>
        <span className="mbl-characteristics">
          <span>{roomName(item.rooms)}</span><span className="mbl-info-dot" aria-hidden="true" />
          <span>{item.area_m2 != null ? `${item.area_m2} м²` : "Площадь не указана"}</span>
        </span>
        <span className="mbl-location"><span aria-hidden="true">⌖</span> {item.district || item.address || "Батуми"}</span>
        <span className="mbl-open">Подробнее о квартире <span aria-hidden="true">↗</span></span>
      </button>
    </article>
  );
}

export function ListPage() {
  const { filters, setFilters } = useFilters();
  const navigate = useNavigate();
  const [items, setItems] = useState<Card[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [pendingFavorites, setPendingFavorites] = useState<number[]>([]);
  const pageRef = useRef(1);
  const requestId = useRef(0);

  const fetchPage = useCallback(async (page: number, append: boolean) => {
    const seq = ++requestId.current;
    if (append) setLoadingMore(true);
    else { setLoading(true); setItems([]); pageRef.current = 1; }
    setError(null);
    try {
      const qs = filtersToParams(filters, { page: String(page), page_size: String(PAGE_SIZE) });
      const data = await api<{ items: Card[]; total: number }>(`/api/public/properties?${qs}`);
      if (seq !== requestId.current) return;
      setItems(prev => append ? [...prev, ...data.items.filter(item => !prev.some(p => p.id === item.id))] : data.items);
      setTotal(data.total);
      pageRef.current = page;
    } catch {
      if (seq === requestId.current) setError("Не удалось загрузить квартиры. Попробуйте ещё раз.");
    } finally {
      if (seq === requestId.current) { setLoading(false); setLoadingMore(false); }
    }
  }, [filters]);

  useEffect(() => {
    void fetchPage(1, false);
    return () => { requestId.current += 1; };
  }, [fetchPage]);

  async function toggleFavorite(id: number) {
    if (pendingFavorites.includes(id)) return;
    setPendingFavorites(prev => [...prev, id]);
    const previous = items;
    setItems(prev => prev.map(item => item.id === id ? { ...item, is_favorite: !item.is_favorite } : item));
    try {
      await api(`/api/public/favorites/${id}`, { method: "POST" });
    } catch {
      setItems(previous);
      setError("Не удалось изменить избранное. Проверьте авторизацию Telegram.");
    } finally {
      setPendingFavorites(prev => prev.filter(value => value !== id));
    }
  }

  const activeFilters = filters.rooms.length + filters.amenities.length + Number(filters.price_min != null) + Number(filters.price_max != null) + Number(Boolean(filters.check_in)) + Number(Boolean(filters.check_out));
  const hasMore = items.length < total;

  return (
    <div className="page mbl-page">
      <header className="mbl-header">
        <div className="mbl-toolbar">
          <Link className="mbl-round-btn" to="/map" aria-label="Вернуться к карте">←</Link>
          <span className="mbl-brand">batumi <strong>rent</strong><span className="mbl-brand-dot">.</span></span>
          <Link className="mbl-round-btn" to="/favorites" aria-label="Избранные квартиры"><HeartIcon filled={false} /></Link>
        </div>
        <p className="mbl-eyebrow">АРЕНДА НЕДВИЖИМОСТИ · БАТУМИ</p>
        <h1>Найдите квартиру <span>под себя.</span></h1>
        <p className="mbl-subtitle">Подобрали варианты для комфортной жизни у моря.</p>
        <div className="mbl-segment" role="group" aria-label="Тип аренды">
          <button type="button" className={filters.rent_type === "long_term" ? "active" : ""} aria-pressed={filters.rent_type === "long_term"}
            onClick={() => setFilters(prev => ({ ...prev, rent_type: "long_term" }))}>Долгосрочно</button>
          <button type="button" className={filters.rent_type === "daily" ? "active" : ""} aria-pressed={filters.rent_type === "daily"}
            onClick={() => setFilters(prev => ({ ...prev, rent_type: "daily" }))}>Посуточно</button>
        </div>
      </header>

      <div className="mbl-tools">
        <button type="button" className="mbl-filter-btn" onClick={() => setShowFilters(true)}>
          <span aria-hidden="true">☷</span> Фильтры {activeFilters > 0 && <span className="mbl-count">{activeFilters}</span>}
        </button>
        <label className="mbl-sort"><span className="mbl-sr-only">Сортировка</span>
          <select value={filters.sort || "newest"} onChange={e => setFilters(prev => ({ ...prev, sort: e.target.value }))}>
            <option value="newest">Сначала новые</option><option value="price_asc">Сначала дешевле</option><option value="price_desc">Сначала дороже</option>
          </select><span aria-hidden="true">⌄</span>
        </label>
      </div>
      <div className="mbl-results"><strong>{loading ? "Подбираем квартиры…" : `${total} ${total % 10 === 1 && total % 100 !== 11 ? "вариант" : [2,3,4].includes(total % 10) && !(total % 100 >= 12 && total % 100 <= 14) ? "варианта" : "вариантов"}`}</strong><span>Найдены по вашим параметрам</span></div>

      {error && <div className="mbl-message mbl-error" role="alert">{error}<button type="button" onClick={() => void fetchPage(pageRef.current, pageRef.current > 1)}>Повторить</button></div>}
      {loading && <div className="mbl-grid" aria-label="Загружаем квартиры">{[1,2,3,4].map(n => <div className="mbl-skeleton" key={n}><span/><span/><span/></div>)}</div>}
      {!loading && !items.length && !error && <div className="mbl-message mbl-empty"><span aria-hidden="true">⌂</span><h2>Пока ничего не нашлось</h2><p>Попробуйте расширить бюджет или изменить параметры поиска.</p><button type="button" onClick={() => setShowFilters(true)}>Изменить фильтры</button></div>}
      {!loading && items.length > 0 && <div className="mbl-grid">{items.map(item => <ListingCard key={item.id} item={item} pending={pendingFavorites.includes(item.id)} onFavorite={() => void toggleFavorite(item.id)} onOpen={() => navigate(`/property/${item.id}`)} />)}</div>}
      {!loading && hasMore && <button type="button" className="mbl-more" disabled={loadingMore} onClick={() => void fetchPage(pageRef.current + 1, true)}>{loadingMore ? "Загружаем…" : "Показать ещё квартиры"}</button>}
      <Link to="/map" className="mbl-floating-map"><span aria-hidden="true">⌖</span> Показать на карте</Link>
      {showFilters && <FiltersSheet onClose={() => setShowFilters(false)} />}
    </div>
  );
}
