import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, filtersToParams } from "@/shared/api";
import { useFilters } from "@/shared/filters";
import { FilterBar, PropertyCardItem, StateBox } from "@/shared/ui";
import { FiltersSheet } from "./FiltersSheet";

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

export function ListPage() {
  const { filters, setFilters } = useFilters();
  const [items, setItems] = useState<Card[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  async function load() {
    setLoading(true);
    try {
      const qs = filtersToParams(filters, { page: "1", page_size: "30" });
      const data = await api<{ items: Card[]; total: number }>(`/api/public/properties?${qs}`);
      setItems(data.items);
      setTotal(data.total);
      setError(null);
    } catch {
      setError("Не удалось загрузить список");
    } finally {
      setLoading(false);
    }
  }

  async function toggleFav(id: number) {
    try {
      await api(`/api/public/favorites/${id}`, { method: "POST" });
      await load();
    } catch {
      setError("Войдите через Telegram, чтобы пользоваться избранным");
    }
  }

  return (
    <div className="page">
      <div className="toolbar">
        <Link className="chip" to="/map">
          ← Карта
        </Link>
        <Link className="chip" to="/favorites">
          Избранное
        </Link>
        <select
          className="chip"
          value={filters.sort || "newest"}
          onChange={(e) => setFilters((p) => ({ ...p, sort: e.target.value }))}
        >
          <option value="newest">Сначала новые</option>
          <option value="price_asc">Цена ↑</option>
          <option value="price_desc">Цена ↓</option>
        </select>
      </div>
      <FilterBar
        rentType={filters.rent_type}
        onRentType={(rent_type) => setFilters((p) => ({ ...p, rent_type }))}
        onOpenFilters={() => setShowFilters((v) => !v)}
        resultCount={total}
      />
      {showFilters && <FiltersSheet onClose={() => setShowFilters(false)} />}
      {loading && <StateBox title="Загрузка…" />}
      {error && <StateBox title={error} />}
      {!loading && !items.length && (
        <StateBox title="Ничего не найдено">
          <button className="btn btn-secondary" onClick={() => setShowFilters(true)}>
            Изменить фильтры
          </button>
        </StateBox>
      )}
      <div className="list-grid">
        {items.map((item) => (
          <PropertyCardItem
            key={item.id}
            item={item}
            onOpen={() => navigate(`/property/${item.id}`)}
            onFavorite={() => void toggleFav(item.id)}
          />
        ))}
      </div>
    </div>
  );
}
