import { useEffect, useState } from "react";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Review = {
  id: number;
  rating: number;
  text: string;
  realtor_id: number;
  deal_id: number;
  status: string;
};

export function ReviewsPage() {
  const [items, setItems] = useState<Review[]>([]);
  const [comments, setComments] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await api<Review[]>("/api/admin/reviews?status=pending_moderation"));
    } catch (e) {
      setError((e as Error).message || "Ошибка загрузки");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function act(id: number, action: string) {
    await api(`/api/admin/reviews/${id}/moderate`, {
      method: "POST",
      body: JSON.stringify({ action, comment: comments[id] || null }),
    });
    setComments((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    await load();
  }

  if (loading) return <StateBox title="Загрузка…" />;
  if (error) return <StateBox title={error} />;
  if (!items.length) return <StateBox title="Очередь отзывов пуста" />;

  return (
    <div className="stack">
      {items.map((r) => (
        <div className="card" key={r.id}>
          <strong>
            #{r.id} · {"★".repeat(r.rating)} · сделка {r.deal_id}
          </strong>
          <p>{r.text}</p>
          <input
            placeholder="Причина отклонения"
            value={comments[r.id] || ""}
            onChange={(e) =>
              setComments((prev) => ({ ...prev, [r.id]: e.target.value }))
            }
          />
          <div className="stack" style={{ marginTop: 8 }}>
            <button className="btn btn-primary" onClick={() => void act(r.id, "publish")}>
              Опубликовать
            </button>
            <button className="btn btn-danger" onClick={() => void act(r.id, "reject")}>
              Отклонить
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
