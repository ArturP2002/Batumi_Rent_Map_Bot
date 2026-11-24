import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "@/shared/api";
import "./CommunityPages.css";

export function ReviewPage() {
  const [params] = useSearchParams();
  const dealId = Number(params.get("deal_id") || 0);
  const [rating, setRating] = useState(5);
  const [review, setReview] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (busy || !review.trim() || !Number.isSafeInteger(dealId) || dealId <= 0) return;
    setBusy(true); setError(null);
    try { await api("/api/public/reviews", {method: "POST", body: JSON.stringify({deal_id: dealId, rating, text: review.trim()})}); setDone(true); }
    catch (e) { setError((e as Error).message || "Не удалось отправить отзыв. Проверьте статус сделки."); }
    finally { setBusy(false); }
  }

  return <div className="page mbc-page"><header className="mbc-top"><Link to="/map" className="mbc-back" aria-label="К карте">←</Link><span className="mbc-brand">batumi <strong>rent.</strong></span></header>
    {!Number.isSafeInteger(dealId) || dealId <= 0 ? <div className="mbc-empty"><h2>Нет подтверждённой сделки</h2><p>Форма отзыва открывается по ссылке, полученной после подтверждения аренды.</p><Link to="/map" className="mbc-primary">Вернуться к карте</Link></div> : done ? <div className="mbc-success"><span aria-hidden>✓</span><h1>Спасибо за отзыв!</h1><p>Мы отправили его на модерацию. После проверки он появится в профиле риелтора.</p><Link className="mbc-primary" to="/map">Вернуться к карте ↗</Link></div> : <>
    <div className="mbc-heading"><span className="mbc-overline">ПОДТВЕРЖДЁННАЯ АРЕНДА · № {dealId}</span><h1>Расскажите о <em>своём опыте.</em></h1><p>Ваша оценка поможет другим найти надёжного риелтора.</p></div>
    <div className="mbc-form"><h2>Как прошла аренда?</h2><p>Выберите оценку от 1 до 5 звёзд</p><div className="mbc-rating" role="group" aria-label="Оценка риелтора">{[1,2,3,4,5].map(n => <button key={n} type="button" onClick={() => setRating(n)} aria-label={`${n} из 5`} aria-pressed={rating === n} className={n <= rating ? "selected" : ""}>★</button>)}</div>
    <label className="mbc-text-label" htmlFor="mbc-review-text">Ваш отзыв</label><textarea id="mbc-review-text" rows={6} maxLength={1000} value={review} onChange={e => setReview(e.target.value)} placeholder="Расскажите, насколько быстро удалось найти квартиру и как прошла работа с риелтором…"/><div className="mbc-counter">{review.length} / 1000</div>
    <p className="mbc-hint">Отзыв доступен только после подтверждения сделки риелтором, клиентом и администратором.</p>
    {error && <div className="mbc-alert" role="alert">{error}</div>}
    <button type="button" className="mbc-primary mbc-submit" disabled={busy || !review.trim()} onClick={() => void submit()}>{busy ? "Отправляем…" : "Отправить отзыв"}<span aria-hidden>→</span></button></div></>}
  </div>;
}
