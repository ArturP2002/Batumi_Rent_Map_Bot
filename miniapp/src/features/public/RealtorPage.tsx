import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api";
import { PropertyCardItem, StateBox } from "@/shared/ui";

export function RealtorPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api(`/api/public/realtors/${id}`)
      .then(setData)
      .catch(() => setError("Профиль не найден"));
  }, [id]);

  if (error) return <StateBox title={error} />;
  if (!data) return <StateBox title="Загрузка…" />;

  return (
    <div className="page">
      <Link className="chip" to={-1 as unknown as string} onClick={(e) => { e.preventDefault(); navigate(-1); }}>
        ← Назад
      </Link>
      <div className="card" style={{ marginTop: 12 }}>
        <h2 style={{ marginTop: 0 }}>{data.display_name}</h2>
        <div className="muted">
          ★ {data.rating_avg} · {data.rating_count} отзывов · {data.active_listings} объектов
        </div>
        <p>{data.bio || "Пока нет описания"}</p>
      </div>
      <h3>Отзывы</h3>
      {!data.reviews?.length && <div className="muted">Пока нет отзывов</div>}
      <div className="stack">
        {data.reviews?.map((r: any) => (
          <div className="card" key={r.id}>
            <strong>{"★".repeat(r.rating)}</strong>
            <p style={{ marginBottom: 0 }}>{r.text}</p>
          </div>
        ))}
      </div>
      <h3>Объявления</h3>
      <div className="stack">
        {data.properties?.map((p: any) => (
          <PropertyCardItem key={p.id} item={p} onOpen={() => navigate(`/property/${p.id}`)} />
        ))}
      </div>
    </div>
  );
}
