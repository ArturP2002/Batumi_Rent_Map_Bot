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

export function DashboardPage() {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api<Dashboard>("/api/admin/dashboard")
      .then(setData)
      .catch((e) => setError((e as Error).message || "Ошибка дашборда"));
  }, []);

  if (error) return <StateBox title={error} />;
  if (!data) return <StateBox title="Загрузка дашборда…" />;

  const kpis = [
    ["Активные", data.active_properties],
    ["На модерации", data.moderation_properties],
    ["Риелторы", data.active_realtors],
    ["Обращения", data.inquiries_open],
    ["Сделки", data.deals_pending],
    ["Отзывы", data.reviews_pending],
  ] as const;

  return (
    <>
      <div className="kpi-grid">
        {kpis.map(([label, value]) => (
          <div className="kpi" key={label}>
            <span className="muted">{label}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
      <h3>Требует действия</h3>
      {!data.attention.length && <div className="muted">Очередь пуста</div>}
      <div className="stack">
        {data.attention.map((a) => (
          <Link
            key={`${a.type}-${a.id}`}
            className="card"
            to={
              a.type.includes("deal")
                ? "/admin/deals"
                : a.type.includes("review")
                  ? "/admin/reviews"
                  : "/admin/listings"
            }
          >
            <strong>{a.title}</strong>
            <div className="muted">{a.type}</div>
          </Link>
        ))}
      </div>
    </>
  );
}
