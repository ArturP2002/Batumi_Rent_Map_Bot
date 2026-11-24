import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "@/shared/api";
import { StateBox } from "@/shared/ui";
import "./AdminWorkflow.css";

type Listing = {
  id: number;
  public_code: string;
  price_usd: number;
  rooms: string;
  status: string;
  district?: string | null;
  address?: string | null;
  cover_url?: string | null;
};
type Detail = Listing & {
  description?: string | null;
  photos?: { id: number; url: string; thumb_url?: string | null }[];
  rent_type?: string;
};
type Interval = { id: number; start_date: string; end_date: string; kind: string; note?: string | null };

const PAGE_SIZE = 30;
const SEARCH_DEBOUNCE_MS = 320;
const statuses: Record<string, string> = {
  moderation: "На модерации",
  active: "Активные",
  needs_fix: "Нужны правки",
  hidden: "Скрытые",
  blocked: "Заблокированные",
};
const actions = [
  { id: "approve", name: "Одобрить", tone: "primary" },
  { id: "needs_fix", name: "Отправить на правки", tone: "neutral" },
  { id: "reject", name: "Отклонить", tone: "danger" },
  { id: "hide", name: "Скрыть", tone: "neutral" },
  { id: "restore", name: "Восстановить", tone: "primary" },
] as const;
const currency = (n: number) => `$${Number(n).toLocaleString("en-US")}`;

export function ListingsPage() {
  const [status, setStatus] = useState("moderation");
  const [items, setItems] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Detail | null>(null);
  const [intervals, setIntervals] = useState<Interval[]>([]);
  const [comment, setComment] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [opening, setOpening] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const abortRef = useRef<AbortController | null>(null);
  const loadSeqRef = useRef(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setQuery(searchInput.trim()), SEARCH_DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    setPage(1);
    setSelected(null);
    void load(1, false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, query]);

  async function load(pageNum: number, append: boolean) {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const requestId = ++loadSeqRef.current;
    if (append) setLoadingMore(true);
    else {
      setLoading(true);
      setItems([]);
    }
    setError("");
    try {
      const params = new URLSearchParams({
        status,
        page: String(pageNum),
        page_size: String(PAGE_SIZE),
      });
      if (query) params.set("q", query);
      const data = await api<{ items: Listing[]; total: number }>(`/api/admin/properties?${params}`, {
        signal: ac.signal,
      });
      if (requestId !== loadSeqRef.current) return;
      setItems((prev) =>
        append
          ? [
              ...prev,
              ...data.items.filter((item) => !prev.some((existing) => existing.id === item.id)),
            ]
          : data.items,
      );
      setTotal(data.total);
      setPage(pageNum);
    } catch (e) {
      if ((e as Error).name === "AbortError" || requestId !== loadSeqRef.current) return;
      setError((e as Error).message || "Не удалось загрузить объекты");
      if (!append) {
        setItems([]);
        setTotal(0);
      }
    } finally {
      if (requestId === loadSeqRef.current) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }

  async function open(id: number) {
    setOpening(true);
    setError("");
    setComment("");
    setStart("");
    setEnd("");
    setIntervals([]);
    try {
      const d = await api<Detail>(`/api/admin/properties/${id}`);
      setSelected(d);
      try {
        setIntervals(await api<Interval[]>(`/api/admin/properties/${id}/calendar`));
      } catch {
        setNotice("Календарь не загрузился. Попробуйте открыть объект ещё раз.");
      }
    } catch (e) {
      setError((e as Error).message || "Не удалось открыть объявление");
    } finally {
      setOpening(false);
    }
  }

  async function act(action: string) {
    if (!selected || busy) return;
    if ((action === "reject" || action === "needs_fix") && !comment.trim()) {
      setError("Укажите причину для отклонения или отправки на исправление");
      return;
    }
    if (
      !window.confirm(
        `Подтвердить действие «${actions.find((a) => a.id === action)?.name || action}» для ${selected.public_code}?`,
      )
    ) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/properties/${selected.id}/moderate`, {
        method: "POST",
        body: JSON.stringify({ action, comment: comment.trim() || null }),
      });
      setSelected(null);
      setNotice("Статус объявления обновлён");
      await load(1, false);
    } catch (e) {
      setError((e as Error).message || "Не удалось обновить статус");
    } finally {
      setBusy(false);
    }
  }

  async function addInterval() {
    if (!selected || busy) return;
    if (!start || !end || end <= start) {
      setError("Дата окончания должна быть позже начала");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/properties/${selected.id}/calendar`, {
        method: "POST",
        body: JSON.stringify({ start_date: start, end_date: end, kind: "blocked" }),
      });
      setIntervals(await api<Interval[]>(`/api/admin/properties/${selected.id}/calendar`));
      setStart("");
      setEnd("");
      setNotice("Период добавлен");
    } catch (e) {
      setError((e as Error).message || "Не удалось добавить период");
    } finally {
      setBusy(false);
    }
  }

  async function removeInterval(id: number) {
    if (!selected || busy || !window.confirm("Удалить этот период из календаря?")) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/calendar/${id}`, { method: "DELETE" });
      setIntervals(await api<Interval[]>(`/api/admin/properties/${selected.id}/calendar`));
      setNotice("Период удалён");
    } catch (e) {
      setError((e as Error).message || "Не удалось удалить период");
    } finally {
      setBusy(false);
    }
  }

  const hasMore = items.length < total;

  return (
    <div className="mbw-page">
      <header className="mbw-heading">
        <span className="mbw-eyebrow">КАТАЛОГ · МОДЕРАЦИЯ</span>
        <h1>
          Объявления<span>.</span>
        </h1>
        <p>Проверка квартир, управление статусами и календарями.</p>
      </header>

      <div className="mbw-toolbar">
        <div className="mbw-tabs" role="group" aria-label="Статус объявления">
          {Object.entries(statuses).map(([key, value]) => (
            <button
              key={key}
              type="button"
              className={status === key ? "active" : ""}
              aria-pressed={status === key}
              onClick={() => setStatus(key)}
            >
              {value}
            </button>
          ))}
        </div>
        <label className="mbw-search">
          <span>⌕</span>
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Код, район или адрес"
            aria-label="Поиск по объявлениям"
          />
        </label>
      </div>

      {!loading && (
        <p className="mbw-hint">
          Найдено: {total}
          {query ? ` по запросу «${query}»` : ""}
          {items.length && items.length < total ? ` · показано ${items.length}` : ""}
        </p>
      )}

      {error && (
        <div className="mbw-alert" role="alert">
          {error}
        </div>
      )}
      {notice && (
        <div className="mbw-note" role="status">
          {notice}
          <button type="button" onClick={() => setNotice("")} aria-label="Закрыть сообщение">
            ×
          </button>
        </div>
      )}

      {loading ? (
        <StateBox title="Загружаем объявления…" />
      ) : !items.length ? (
        <div className="mbw-empty">По выбранным параметрам объявлений нет.</div>
      ) : (
        <>
          <div className="mbw-list">
            {items.map((i) => (
              <button
                type="button"
                className="mbw-listing"
                key={i.id}
                onClick={() => void open(i.id)}
                disabled={opening}
              >
                <span className="mbw-photo">
                  {i.cover_url ? <img src={i.cover_url} alt="" loading="lazy" /> : "⌂"}
                </span>
                <span className="mbw-listing-info">
                  <strong>{i.public_code}</strong>
                  <small>
                    {i.district || i.address || "Батуми"} · {i.rooms}
                  </small>
                  <span className="mbw-price">{currency(i.price_usd)}</span>
                </span>
                <span className={`mbw-status is-${i.status}`}>{statuses[i.status] || i.status}</span>
                <span className="mbw-arrow">↗</span>
              </button>
            ))}
          </div>
          {hasMore && (
            <button
              type="button"
              className="mbw-btn neutral mbw-load-more"
              disabled={loadingMore}
              onClick={() => void load(page + 1, true)}
            >
              {loadingMore ? "Загружаем…" : `Показать ещё · осталось ${total - items.length}`}
            </button>
          )}
        </>
      )}

      {selected && (
        <div
          className="mbw-overlay"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget && !busy) setSelected(null);
          }}
        >
          <section className="mbw-detail" role="dialog" aria-modal="true" aria-labelledby="mbw-detail-title">
            <header className="mbw-detail-top">
              <div>
                <span className="mbw-eyebrow">УПРАВЛЕНИЕ ОБЪЕКТОМ</span>
                <h2 id="mbw-detail-title">{selected.public_code}</h2>
              </div>
              <button className="mbw-close" type="button" onClick={() => setSelected(null)} disabled={busy} aria-label="Закрыть">
                ×
              </button>
            </header>
            <div className="mbw-detail-scroll">
              <div className="mbw-detail-hero">
                {selected.photos?.[0]?.url || selected.cover_url ? (
                  <img src={selected.photos?.[0]?.url || selected.cover_url || ""} alt="Фото объекта" />
                ) : (
                  <div className="mbw-no-photo">Нет фотографии</div>
                )}
                <div>
                  <span className={`mbw-status is-${selected.status}`}>
                    {statuses[selected.status] || selected.status}
                  </span>
                  <h3>{currency(selected.price_usd)}</h3>
                  <p>{selected.address || selected.district || "Адрес не указан"}</p>
                  <small>
                    {selected.rooms} · {selected.rent_type === "daily" ? "Посуточно" : "Долгосрочно"}
                  </small>
                </div>
              </div>

              {selected.description && (
                <section className="mbw-section">
                  <h3>Описание</h3>
                  <p className="mbw-description">{selected.description}</p>
                </section>
              )}

              <section className="mbw-section">
                <div className="mbw-section-heading">
                  <h3>Модерация</h3>
                  <Link to={`/property/${selected.id}`} target="_blank" rel="noreferrer">
                    Посмотреть объявление ↗
                  </Link>
                </div>
                <label className="mbw-field">
                  Комментарий для риелтора
                  <textarea
                    rows={3}
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    placeholder="Причина замечания или отклонения"
                  />
                </label>
                <div className="mbw-actions">
                  {actions
                    .filter((a) =>
                      a.id === "restore"
                        ? selected.status !== "active"
                        : a.id === "approve"
                          ? selected.status === "moderation" || selected.status === "needs_fix"
                          : a.id === "hide"
                            ? selected.status === "active"
                            : selected.status !== "blocked",
                    )
                    .map((a) => (
                      <button
                        key={a.id}
                        type="button"
                        className={`mbw-btn ${a.tone}`}
                        disabled={busy}
                        onClick={() => void act(a.id)}
                      >
                        {a.name}
                      </button>
                    ))}
                </div>
              </section>

              <section className="mbw-section">
                <h3>Календарь занятости</h3>
                <p className="mbw-hint">
                  Период считается от даты начала до даты окончания, не включая день окончания.
                </p>
                {intervals.length ? (
                  <div className="mbw-intervals">
                    {intervals.map((iv) => (
                      <div key={iv.id}>
                        <span>
                          <strong>
                            {iv.start_date} — {iv.end_date}
                          </strong>
                          <small>
                            {iv.kind}
                            {iv.note ? ` · ${iv.note}` : ""}
                          </small>
                        </span>
                        <button type="button" disabled={busy} onClick={() => void removeInterval(iv.id)}>
                          Удалить
                        </button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mbw-hint">Периодов нет.</p>
                )}
                <div className="mbw-two-fields">
                  <label className="mbw-field">
                    С даты
                    <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
                  </label>
                  <label className="mbw-field">
                    По дату (не включая)
                    <input type="date" value={end} min={start || undefined} onChange={(e) => setEnd(e.target.value)} />
                  </label>
                </div>
                <button
                  type="button"
                  className="mbw-btn neutral"
                  disabled={busy || !start || !end || end <= start}
                  onClick={() => void addInterval()}
                >
                  + Заблокировать период
                </button>
              </section>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
