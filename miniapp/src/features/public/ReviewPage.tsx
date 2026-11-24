import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

export function ReviewPage() {
  const [params] = useSearchParams();
  const dealId = Number(params.get("deal_id") || 0);
  const [rating, setRating] = useState(5);
  const [text, setText] = useState("");
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    try {
      await api("/api/public/reviews", {
        method: "POST",
        body: JSON.stringify({ deal_id: dealId, rating, text }),
      });
      setDone(true);
    } catch (e) {
      setError((e as Error).message || "Не удалось отправить. Нужна подтверждённая сделка.");
    }
  }

  if (!dealId) return <StateBox title="Нужен deal_id подтверждённой сделки" />;
  if (done) {
    return (
      <div className="page">
        <StateBox title="Отзыв отправлен на модерацию" />
        <Link className="btn btn-primary btn-block" to="/">
          На главную
        </Link>
      </div>
    );
  }

  return (
    <div className="page">
      <h2>Оставить отзыв</h2>
      <div className="field">
        <label>Оценка</label>
        <select value={rating} onChange={(e) => setRating(Number(e.target.value))}>
          {[5, 4, 3, 2, 1].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
      </div>
      <div className="field">
        <label>Текст (до 1000)</label>
        <textarea
          rows={5}
          maxLength={1000}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>
      {error && <div className="muted">{error}</div>}
      <button className="btn btn-primary btn-block" onClick={() => void submit()}>
        Отправить отзыв
      </button>
    </div>
  );
}
