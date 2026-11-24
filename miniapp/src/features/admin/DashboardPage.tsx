import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Dashboard = {
  active_properties: number;
  moderation_properties: number;
  active_realtors: number;
  inquiries_open: number;
  deals_pending: number;
  reviews_pending: number;
  attention: { type: string; id: number; title: string }[];
};

const cards = [
  { key: "active_properties", title: "Активные квартиры", icon: "⌂", to: "/admin/listings" },
  { key: "moderation_properties", title: "На модерации", icon: "◷", to: "/admin/listings" },
  { key: "active_realtors", title: "Риелторы", icon: "♙", to: "/admin/realtors" },
  { key: "inquiries_open", title: "Обращения", icon: "↗", to: "/admin/stats" },
  { key: "deals_pending", title: "Сделки на проверке", icon: "◇", to: "/admin/deals" },
  { key: "reviews_pending", title: "Отзывы на проверке", icon: "☆", to: "/admin/reviews" },
] as const;

function target(type: string) {
  if (type.includes("deal")) return "/admin/deals";
  if (type.includes("review")) return "/admin/reviews";
  return "/admin/listings";
}

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const reload = async () => {
    setBusy(true); setError("");
    try { setData(await api<Dashboard>("/api/admin/dashboard")); }
    catch (e) { setError((e as Error).message || "Не удалось загрузить обзор"); }
    finally { setBusy(false); }
  };
  useEffect(() => { void reload(); }, []);
  return <>
    <header className="mba-page-heading"><div><div className="mba-overline">ОБЗОР ПЛАТФОРМЫ</div><h1>Панель управления<span>.</span></h1><p>Все важные показатели и задачи — в одном месте.</p></div><button type="button" className="mba-outline-action" disabled={busy} onClick={() => void reload()}>{busy ? "Обновляем…" : "↻ Обновить"}</button></header>
    {error && <div className="mba-alert" role="alert">{error} <button type="button" onClick={() => void reload()}>Повторить</button></div>}
    {!data && busy && <StateBox title="Загружаем показатели…" />}
    {data && <>
      <div className="mba-kpis">{cards.map(({key,title,icon,to},i) => <Link key={key} to={to} className={`mba-kpi ${i===1 || i===4 || i===5 ? "mba-kpi-action" : ""}`}><div className="mba-kpi-top"><span>{title}</span><span className="mba-kpi-icon">{icon}</span></div><strong>{data[key].toLocaleString("ru-RU")}</strong><span className="mba-kpi-foot">{i===1 || i===4 || i===5 ? "Перейти к проверке ↗" : "Открыть раздел ↗"}</span></Link>)}</div>
      <section className="mba-section"><div className="mba-section-heading"><div><span className="mba-overline">ВАШИ ЗАДАЧИ</span><h2>Требует внимания</h2></div><span className="mba-count-pill">{data.attention.length}</span></div>
        {data.attention.length === 0 ? <div className="mba-empty"><span>✓</span><strong>На сегодня всё обработано</strong><p>Новых задач для проверки пока нет.</p></div> : <div className="mba-attention">{data.attention.map(a => <Link className="mba-attention-row" to={target(a.type)} key={`${a.type}-${a.id}`}><span className="mba-attention-dot"/><span><strong>{a.title}</strong><small>{a.type.replace(/_/g, " ")}</small></span><span className="mba-chevron">↗</span></Link>)}</div>}
      </section>
      <section className="mba-section"><div className="mba-section-heading"><div><span className="mba-overline">БЫСТРЫЕ ПЕРЕХОДЫ</span><h2>Рабочие разделы</h2></div></div><div className="mba-shortcuts"><Link to="/admin/listings">⌂ <span>Объявления</span> ↗</Link><Link to="/admin/realtors">♙ <span>Риелторы</span> ↗</Link><Link to="/admin/stats">▥ <span>Аналитика</span> ↗</Link></div></section>
    </>}
  </>;
}
