import { useEffect, useState } from "react";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";

type Card = {
  id: number;
  public_code: string;
  price_usd: number;
  rooms: string;
  status: string;
  district?: string;
  cover_url?: string;
};

type Interval = {
  id: number;
  start_date: string;
  end_date: string;
  kind: string;
  note?: string | null;
};

const STATUS_RU: Record<string, string> = {
  moderation: "на модерации",
  active: "активные",
  needs_fix: "нужны правки",
  hidden: "скрытые",
  blocked: "заблокированные",
};

export function ListingsPage() {
  const [status, setStatus] = useState("moderation");
  const [items, setItems] = useState<Card[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [comment, setComment] = useState("");
  const [intervals, setIntervals] = useState<Interval[]>([]);
  const [calStart, setCalStart] = useState("");
  const [calEnd, setCalEnd] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api<{ items: Card[] }>(
        `/api/admin/properties?status=${status}&page_size=50`,
      );
      setItems(data.items);
    } catch (e) {
      setError((e as Error).message || "Ошибка загрузки");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [status]);

  async function open(id: number) {
    try {
      const detail = await api(`/api/admin/properties/${id}`);
      setSelected(detail);
      setIntervals(await api<Interval[]>(`/api/admin/properties/${id}/calendar`));
    } catch (e) {
      setError((e as Error).message || "Не удалось открыть");
    }
  }

  async function act(action: string) {
    if (!selected) return;
    await api(`/api/admin/properties/${selected.id}/moderate`, {
      method: "POST",
      body: JSON.stringify({ action, comment }),
    });
    setSelected(null);
    setComment("");
    await load();
  }

  async function addInterval() {
    if (!selected || !calStart || !calEnd) return;
    await api(`/api/admin/properties/${selected.id}/calendar`, {
      method: "POST",
      body: JSON.stringify({
        start_date: calStart,
        end_date: calEnd,
        kind: "blocked",
      }),
    });
    setCalStart("");
    setCalEnd("");
    setIntervals(await api<Interval[]>(`/api/admin/properties/${selected.id}/calendar`));
  }

  async function removeInterval(intervalId: number) {
    await api(`/api/admin/calendar/${intervalId}`, { method: "DELETE" });
    if (selected) {
      setIntervals(await api<Interval[]>(`/api/admin/properties/${selected.id}/calendar`));
    }
  }

  return (
    <>
      <div className="toolbar">
        {["moderation", "active", "needs_fix", "hidden", "blocked"].map((s) => (
          <button
            key={s}
            className={`chip ${status === s ? "active" : ""}`}
            onClick={() => setStatus(s)}
          >
            {STATUS_RU[s] || s}
          </button>
        ))}
      </div>
      {loading && <StateBox title="Загрузка…" />}
      {error && <StateBox title={error} />}
      {!loading && !items.length && !error && <StateBox title="Пусто" />}
      <div className="stack">
        {items.map((item) => (
          <button key={item.id} className="card" onClick={() => void open(item.id)}>
            <strong>
              #{item.id} {item.public_code}
            </strong>
            <div className="muted">
              ${item.price_usd} · {item.rooms} · {item.district || "—"} · {item.status}
            </div>
          </button>
        ))}
      </div>
      {selected && (
        <div className="panel" style={{ marginTop: 12 }}>
          <h3>
            {selected.public_code} · ${selected.price_usd}
          </h3>
          <p className="muted">{selected.address}</p>
          <p>{selected.description}</p>
          <div className="field">
            <label>Комментарий</label>
            <textarea value={comment} onChange={(e) => setComment(e.target.value)} />
          </div>
          <div className="stack">
            <button className="btn btn-primary" onClick={() => void act("approve")}>
              Одобрить
            </button>
            <button className="btn btn-secondary" onClick={() => void act("needs_fix")}>
              На исправление
            </button>
            <button className="btn btn-danger" onClick={() => void act("reject")}>
              Отклонить
            </button>
            <button className="btn btn-secondary" onClick={() => void act("hide")}>
              Скрыть
            </button>
          </div>

          <h4>Календарь занятости</h4>
          {!intervals.length && <div className="muted">Интервалов нет</div>}
          <div className="stack">
            {intervals.map((iv) => (
              <div className="card" key={iv.id}>
                <div className="muted">
                  {iv.start_date} → {iv.end_date} ({iv.kind})
                </div>
                <button className="btn btn-danger" onClick={() => void removeInterval(iv.id)}>
                  Удалить
                </button>
              </div>
            ))}
          </div>
          <div className="field">
            <label>Заблокировать с</label>
            <input type="date" value={calStart} onChange={(e) => setCalStart(e.target.value)} />
          </div>
          <div className="field">
            <label>по (не включая)</label>
            <input type="date" value={calEnd} onChange={(e) => setCalEnd(e.target.value)} />
          </div>
          <button className="btn btn-secondary btn-block" onClick={() => void addInterval()}>
            Добавить период
          </button>
          <button className="btn btn-secondary" onClick={() => setSelected(null)}>
            Закрыть
          </button>
        </div>
      )}
    </>
  );
}
