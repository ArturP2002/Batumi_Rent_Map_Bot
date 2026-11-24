import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "@/shared/api";
import { PropertyCardItem, StateBox } from "@/shared/ui";

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

export function FavoritesPage() {
  const [items, setItems] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await api<Card[]>("/api/public/favorites"));
    } catch {
      setItems([]);
      setError("Нужна авторизация Telegram, чтобы видеть избранное");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function toggleFav(id: number) {
    try {
      await api(`/api/public/favorites/${id}`, { method: "POST" });
      await load();
    } catch {
      setError("Не удалось изменить избранное");
    }
  }

  return (
    <div className="page">
      <div className="toolbar">
        <Link className="chip" to="/map">
          ← Карта
        </Link>
        <Link className="chip" to="/list">
          Список
        </Link>
      </div>
      <h2>Избранное</h2>
      {loading && <StateBox title="Загрузка…" />}
      {error && <StateBox title={error} />}
      {!loading && !error && !items.length && <StateBox title="Пока пусто" />}
      <div className="list-grid">
        {items.map((item) => (
          <PropertyCardItem
            key={item.id}
            item={{ ...item, is_favorite: true }}
            onOpen={() => navigate(`/property/${item.id}`)}
            onFavorite={() => void toggleFav(item.id)}
          />
        ))}
      </div>
    </div>
  );
}
