import { useEffect, useState } from "react";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Settings = {
  freshness_days: number;
  freshness_remind_days: number;
  freshness_hide_days: number;
  districts: string[];
};

export function SettingsPage() {
  const [data, setData] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    void api<Settings>("/api/admin/settings").then(setData);
  }, []);

  async function save() {
    if (!data) return;
    setData(await api<Settings>("/api/admin/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    }));
    setSaved(true);
  }

  if (!data) return <StateBox title="Загрузка…" />;

  return (
    <div className="panel">
      <div className="field">
        <label>Запрос актуальности (дней)</label>
        <input
          type="number"
          value={data.freshness_days}
          onChange={(e) => setData({ ...data, freshness_days: Number(e.target.value) })}
        />
      </div>
      <div className="field">
        <label>Напоминание (+дней)</label>
        <input
          type="number"
          value={data.freshness_remind_days}
          onChange={(e) =>
            setData({ ...data, freshness_remind_days: Number(e.target.value) })
          }
        />
      </div>
      <div className="field">
        <label>Скрытие (+дней)</label>
        <input
          type="number"
          value={data.freshness_hide_days}
          onChange={(e) => setData({ ...data, freshness_hide_days: Number(e.target.value) })}
        />
      </div>
      <div className="field">
        <label>Районы (через запятую)</label>
        <textarea
          value={data.districts.join(", ")}
          onChange={(e) =>
            setData({
              ...data,
              districts: e.target.value.split(",").map((x) => x.trim()).filter(Boolean),
            })
          }
        />
      </div>
      <button className="btn btn-primary btn-block" onClick={() => void save()}>
        Сохранить
      </button>
      {saved && <div className="muted">Сохранено</div>}
    </div>
  );
}
