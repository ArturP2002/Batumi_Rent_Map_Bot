import { useEffect, useState } from "react";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Deal = {
  id: number;
  property_id: number;
  realtor_id: number;
  client_user_id: number;
  status: string;
  start_date?: string;
  end_date?: string;
  confirmations: { side: string; decision: string }[];
};

export function DealsPage() {
  const [items, setItems] = useState<Deal[]>([]);
  const [comments, setComments] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setItems(await api<Deal[]>("/api/admin/deals?status=pending"));
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

  async function decide(id: number, decision: "approved" | "rejected") {
    await api(`/api/admin/deals/${id}/decide`, {
      method: "POST",
      body: JSON.stringify({ decision, comment: comments[id] || null }),
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
  if (!items.length) return <StateBox title="Нет сделок на проверке" />;

  return (
    <div className="stack">
      {items.map((d) => (
        <div className="card" key={d.id}>
          <strong>Сделка #{d.id}</strong>
          <div className="muted">
            объект {d.property_id} · риелтор {d.realtor_id} · клиент {d.client_user_id}
          </div>
          <div className="muted">
            {d.start_date || "—"} → {d.end_date || "—"}
          </div>
          <div className="muted">
            {d.confirmations.map((c) => `${c.side}:${c.decision}`).join(" · ")}
          </div>
          <div className="field">
            <label>Комментарий</label>
            <input
              value={comments[d.id] || ""}
              onChange={(e) =>
                setComments((prev) => ({ ...prev, [d.id]: e.target.value }))
              }
            />
          </div>
          <div className="stack">
            <button className="btn btn-primary" onClick={() => void decide(d.id, "approved")}>
              Подтвердить
            </button>
            <button className="btn btn-danger" onClick={() => void decide(d.id, "rejected")}>
              Отклонить
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
