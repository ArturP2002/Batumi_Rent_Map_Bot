import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Deal = {
  id: number;
  property_id: number;
  status: string;
  start_date?: string | null;
  end_date?: string | null;
  confirmations: { side: string; decision: string }[];
};

export function DealConfirmPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [deal, setDeal] = useState<Deal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);

  useEffect(() => {
    void api<Deal>(`/api/public/deals/${id}`)
      .then(setDeal)
      .catch((e) => setError((e as Error).message || "Не удалось загрузить сделку"));
  }, [id]);

  async function decide(decision: "approved" | "rejected") {
    if (!deal || busy) return;
    setBusy(true);
    try {
      const updated = await api<Deal>(`/api/public/deals/${deal.id}/decide`, {
        method: "POST",
        body: JSON.stringify({ decision }),
      });
      setDeal(updated);
      setDone(decision === "approved" ? "Вы подтвердили аренду" : "Вы отклонили аренду");
      if (decision === "approved" && updated.status === "confirmed") {
        setTimeout(() => navigate(`/review?deal_id=${deal.id}`), 1200);
      }
    } catch (e) {
      setError((e as Error).message || "Ошибка сохранения");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <StateBox title={error} />;
  if (!deal) return <StateBox title="Загрузка сделки…" />;

  const client = deal.confirmations.find((c) => c.side === "client");
  const already = client && client.decision !== "pending";

  return (
    <div className="page">
      <Link className="chip" to="/">
        ← На главную
      </Link>
      <h2>Подтверждение аренды</h2>
      <div className="card">
        <strong>Сделка №{deal.id}</strong>
        <div className="muted">Объект #{deal.property_id}</div>
        <div className="muted">
          Даты: {deal.start_date || "—"} → {deal.end_date || "—"}
        </div>
        <div className="muted">Статус: {deal.status}</div>
        <div className="muted" style={{ marginTop: 8 }}>
          {deal.confirmations
            .map((c) => `${c.side}: ${c.decision}`)
            .join(" · ")}
        </div>
      </div>
      {done && <StateBox title={done} />}
      {!already && !done && deal.status === "pending" && (
        <div className="stack" style={{ marginTop: 12 }}>
          <button
            className="btn btn-primary btn-block"
            disabled={busy}
            onClick={() => void decide("approved")}
          >
            Подтвердить аренду
          </button>
          <button
            className="btn btn-danger btn-block"
            disabled={busy}
            onClick={() => void decide("rejected")}
          >
            Отклонить
          </button>
        </div>
      )}
      {already && deal.status === "confirmed" && (
        <Link className="btn btn-primary btn-block" to={`/review?deal_id=${deal.id}`}>
          Оставить отзыв
        </Link>
      )}
      <Link className="btn btn-secondary btn-block" to={`/property/${deal.property_id}`}>
        Открыть объявление
      </Link>
    </div>
  );
}
