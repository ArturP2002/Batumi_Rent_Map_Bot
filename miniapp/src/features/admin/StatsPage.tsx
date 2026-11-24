import { useEffect, useState } from "react";
import { api, apiBlob } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Stats = {
  users: number;
  new_users: number;
  property_views: number;
  contact_clicks: number;
  inquiries: number;
  deals_confirmed: number;
  reviews_published: number;
  conversions: Record<string, number>;
  top_properties: { property_id: number; views: number }[];
  series: { day: string; property_views: number }[];
};

function defaultFrom() {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().slice(0, 10);
}

function defaultTo() {
  return new Date().toISOString().slice(0, 10);
}

export function StatsPage() {
  const [data, setData] = useState<Stats | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fromDate, setFromDate] = useState(defaultFrom);
  const [toDate, setToDate] = useState(defaultTo);

  async function load() {
    setError(null);
    try {
      const qs = new URLSearchParams({ from_date: fromDate, to_date: toDate });
      setData(await api<Stats>(`/api/admin/stats?${qs}`));
    } catch (e) {
      setData(null);
      setError((e as Error).message || "Не удалось загрузить статистику");
    }
  }

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function exportFile(format: "csv" | "xlsx") {
    const qs = new URLSearchParams({
      format,
      from_date: fromDate,
      to_date: toDate,
    });
    const blob = await apiBlob(`/api/admin/stats/export?${qs}`);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `stats.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <>
      <div className="panel">
        <div className="field">
          <label>С даты</label>
          <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} />
        </div>
        <div className="field">
          <label>По дату</label>
          <input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} />
        </div>
        <button className="btn btn-primary btn-block" onClick={() => void load()}>
          Применить период
        </button>
      </div>
      {error && <StateBox title={error} />}
      {!data && !error && <StateBox title="Считаем метрики…" />}
      {data && (
        <>
          <div className="kpi-grid">
            {(
              [
                ["Пользователи", data.users],
                ["Новые", data.new_users],
                ["Просмотры", data.property_views],
                ["Клики", data.contact_clicks],
                ["Обращения", data.inquiries],
                ["Сделки", data.deals_confirmed],
              ] as const
            ).map(([k, v]) => (
              <div className="kpi" key={k}>
                <span className="muted">{k}</span>
                <strong>{v}</strong>
              </div>
            ))}
          </div>
          <h3>Конверсии</h3>
          <div className="card">
            {Object.entries(data.conversions).map(([k, v]) => (
              <div key={k}>
                {k}: {(v * 100).toFixed(1)}%
              </div>
            ))}
          </div>
          <h3>Топ объявлений</h3>
          <div className="stack">
            {data.top_properties.map((p) => (
              <div className="card" key={p.property_id}>
                #{p.property_id} — {p.views} просмотров
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-block" onClick={() => void exportFile("csv")}>
            Экспорт CSV
          </button>
          <button className="btn btn-secondary btn-block" onClick={() => void exportFile("xlsx")}>
            Экспорт XLSX
          </button>
        </>
      )}
    </>
  );
}
