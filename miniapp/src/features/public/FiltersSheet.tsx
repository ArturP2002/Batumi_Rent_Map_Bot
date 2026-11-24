import { useEffect, useState } from "react";
import type { FiltersState } from "@/shared/api";
import { AMENITIES, ROOM_OPTIONS, roomLabel, useFilters } from "@/shared/filters";
import "./FiltersSheet.css";

const GROUPS: { title: string; keys: string[] }[] = [
  { title: "Комфорт", keys: ["wifi", "air_conditioning", "furniture", "central_heating", "hot_water", "tv"] },
  { title: "Кухня и техника", keys: ["kitchen", "oven", "microwave", "dishwasher", "washing_machine"] },
  { title: "Дом и расположение", keys: ["parking", "balcony", "elevator", "sea_view", "mountain_view", "bedrooms_with_windows"] },
  { title: "Условия проживания", keys: ["pets_allowed"] },
];

const clone = (f: FiltersState): FiltersState => ({ ...f, rooms: [...f.rooms], amenities: [...f.amenities] });
const roomTitle = (room: string) => room === "studio" ? "Студия" : room === "4+" ? "4+" : roomLabel(room);

function countActive(f: FiltersState) {
  return f.rooms.length + f.amenities.length + Number(f.price_min != null) + Number(f.price_max != null)
    + Number(Boolean(f.check_in && f.rent_type === "daily")) + Number(Boolean(f.check_out && f.rent_type === "daily"));
}

function ToggleGroup({ title, items, value, onToggle }: {
  title: string;
  items: { key: string; label: string }[];
  value: string[];
  onToggle: (key: string) => void;
}) {
  return (
    <section className="mbf-amenity-group">
      <h4 className="mbf-amenity-title">{title}</h4>
      <div className="mbf-amenity-grid">
        {items.map((item) => {
          const selected = value.includes(item.key);
          return (
            <button key={item.key} type="button" aria-pressed={selected}
              className={`mbf-amenity ${selected ? "is-selected" : ""}`}
              onClick={() => onToggle(item.key)}>
              <span className="mbf-check" aria-hidden>{selected ? "✓" : ""}</span>
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

export function FiltersSheet({ onClose }: { onClose: () => void }) {
  const { filters, setFilters } = useFilters();
  const [draft, setDraft] = useState<FiltersState>(() => clone(filters));
  const [showAll, setShowAll] = useState(false);
  const active = countActive(draft);
  const invalidPrice = draft.price_min != null && draft.price_max != null && draft.price_min > draft.price_max;
  const invalidDates = Boolean(draft.rent_type === "daily" && draft.check_in && draft.check_out && draft.check_out <= draft.check_in);
  const invalid = invalidPrice || invalidDates;

  useEffect(() => {
    const onEscape = (ev: KeyboardEvent) => { if (ev.key === "Escape") onClose(); };
    document.addEventListener("keydown", onEscape);
    return () => document.removeEventListener("keydown", onEscape);
  }, [onClose]);

  function update<K extends keyof FiltersState>(key: K, value: FiltersState[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }
  function toggle(key: "rooms" | "amenities", item: string) {
    setDraft((prev) => ({
      ...prev,
      [key]: prev[key].includes(item) ? prev[key].filter((x) => x !== item) : [...prev[key], item],
    }));
  }
  function resetDraft() {
    setDraft((prev) => ({ rent_type: prev.rent_type, rooms: [], amenities: [], sort: prev.sort || "newest" }));
  }
  function apply() {
    if (invalid) return;
    setFilters(clone(draft));
    onClose();
  }
  const groups = showAll ? GROUPS : GROUPS.slice(0, 2);

  return (
    <div className="mbf-overlay" role="presentation" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="mbf-panel" role="dialog" aria-modal="true" aria-labelledby="mbf-title">
        <div className="mbf-handle" aria-hidden="true" />
        <header className="mbf-header">
          <div>
            <div className="mbf-overline">НАСТРОЙКИ ПОИСКА</div>
            <h2 id="mbf-title">Найти квартиру <span className="mbf-heading-dot">.</span></h2>
            <p>Настройте параметры — на карте останутся подходящие варианты.</p>
          </div>
          <button className="mbf-close" type="button" aria-label="Закрыть фильтры без сохранения" onClick={onClose}>×</button>
        </header>

        <div className="mbf-scroll">
          <section className="mbf-section">
            <div className="mbf-section-head"><h3>Тип аренды</h3></div>
            <div className="mbf-segment" role="group" aria-label="Тип аренды">
              <button type="button" className={draft.rent_type === "long_term" ? "is-selected" : ""}
                aria-pressed={draft.rent_type === "long_term"}
                onClick={() => update("rent_type", "long_term")}>Долгосрочно</button>
              <button type="button" className={draft.rent_type === "daily" ? "is-selected" : ""}
                aria-pressed={draft.rent_type === "daily"}
                onClick={() => update("rent_type", "daily")}>Посуточно</button>
            </div>
          </section>

          <section className="mbf-section">
            <div className="mbf-section-head"><h3>Количество комнат</h3><span>Можно выбрать несколько</span></div>
            <div className="mbf-rooms">
              {ROOM_OPTIONS.map((room) => <button type="button" key={room}
                className={draft.rooms.includes(room) ? "is-selected" : ""}
                aria-pressed={draft.rooms.includes(room)} onClick={() => toggle("rooms", room)}>{roomTitle(room)}</button>)}
            </div>
          </section>

          <section className="mbf-section">
            <div className="mbf-section-head"><h3>Бюджет</h3><span>USD {draft.rent_type === "daily" ? "за сутки" : "в месяц"}</span></div>
            <div className="mbf-price-fields">
              <label className="mbf-input-wrap"><span>От</span><div><span>$</span><input type="number" min="0" inputMode="decimal" placeholder="Любая" value={draft.price_min ?? ""} onChange={(e) => update("price_min", e.target.value === "" ? undefined : Math.max(0, Number(e.target.value)))} /></div></label>
              <label className="mbf-input-wrap"><span>До</span><div><span>$</span><input type="number" min="0" inputMode="decimal" placeholder="Любая" value={draft.price_max ?? ""} onChange={(e) => update("price_max", e.target.value === "" ? undefined : Math.max(0, Number(e.target.value)))} /></div></label>
            </div>
            {invalidPrice && <p className="mbf-validation" role="alert">Максимальная цена должна быть не меньше минимальной.</p>}
          </section>

          {draft.rent_type === "daily" && <section className="mbf-section">
            <div className="mbf-section-head"><h3>Даты проживания</h3><span>Без бронирования</span></div>
            <div className="mbf-price-fields">
              <label className="mbf-input-wrap"><span>Заезд</span><div><input type="date" value={draft.check_in || ""} onChange={(e) => update("check_in", e.target.value || undefined)} /></div></label>
              <label className="mbf-input-wrap"><span>Выезд</span><div><input type="date" min={draft.check_in || undefined} value={draft.check_out || ""} onChange={(e) => update("check_out", e.target.value || undefined)} /></div></label>
            </div>
            {invalidDates && <p className="mbf-validation" role="alert">Дата выезда должна быть позднее даты заезда.</p>}
          </section>}

          <section className="mbf-section mbf-last-section">
            <div className="mbf-section-head"><h3>Удобства и особенности</h3><span>{draft.amenities.length} выбрано</span></div>
            {groups.map((group) => <ToggleGroup key={group.title} title={group.title}
              items={group.keys.map((key) => AMENITIES.find((a) => a.key === key)).filter((a): a is (typeof AMENITIES)[number] => Boolean(a))}
              value={draft.amenities} onToggle={(key) => toggle("amenities", key)} />)}
            <button className="mbf-expand" type="button" onClick={() => setShowAll((v) => !v)}>
              {showAll ? "Свернуть дополнительные" : "Показать все удобства"}<span aria-hidden>{showAll ? "↑" : "↓"}</span>
            </button>
          </section>
        </div>

        <footer className="mbf-footer">
          <div className="mbf-footer-head"><span>{active ? `Выбрано параметров: ${active}` : "Без дополнительных ограничений"}</span><button type="button" onClick={resetDraft}>Сбросить всё</button></div>
          <button type="button" className="mbf-apply" disabled={invalid} onClick={apply}>Показать квартиры <span aria-hidden>→</span></button>
        </footer>
      </div>
    </div>
  );
}
