import { AMENITIES, ROOM_OPTIONS, roomLabel, useFilters } from "@/shared/filters";

export function FiltersSheet({ onClose }: { onClose: () => void }) {
  const { filters, setFilters, reset } = useFilters();

  return (
    <div
      className="sheet-backdrop"
      role="presentation"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="sheet" role="dialog" aria-modal="true" aria-label="Фильтры">
        <div className="sheet-handle" />
        <h3 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>Фильтры</h3>
        <div className="field">
          <label>Комнаты</label>
          <div className="toolbar">
            {ROOM_OPTIONS.map((r) => (
              <button
                key={r}
                type="button"
                className={`chip ${filters.rooms.includes(r) ? "active" : ""}`}
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    rooms: prev.rooms.includes(r)
                      ? prev.rooms.filter((x) => x !== r)
                      : [...prev.rooms, r],
                  }))
                }
              >
                {roomLabel(r)}
              </button>
            ))}
          </div>
        </div>
        <div className="price-row">
          <div className="field">
            <label>Цена USD min</label>
            <input
              type="number"
              inputMode="numeric"
              value={filters.price_min ?? ""}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  price_min: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            />
          </div>
          <div className="field">
            <label>Цена USD max</label>
            <input
              type="number"
              inputMode="numeric"
              value={filters.price_max ?? ""}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  price_max: e.target.value ? Number(e.target.value) : undefined,
                }))
              }
            />
          </div>
        </div>
        {filters.rent_type === "daily" && (
          <div className="price-row">
            <div className="field">
              <label>Заезд</label>
              <input
                type="date"
                value={filters.check_in || ""}
                onChange={(e) => setFilters((p) => ({ ...p, check_in: e.target.value }))}
              />
            </div>
            <div className="field">
              <label>Выезд</label>
              <input
                type="date"
                value={filters.check_out || ""}
                onChange={(e) => setFilters((p) => ({ ...p, check_out: e.target.value }))}
              />
            </div>
          </div>
        )}
        <div className="field">
          <label>Дополнительно</label>
          <div className="amenity-grid">
            {AMENITIES.map((a) => (
              <button
                key={a.key}
                type="button"
                className={`chip ${filters.amenities.includes(a.key) ? "active" : ""}`}
                onClick={() =>
                  setFilters((prev) => ({
                    ...prev,
                    amenities: prev.amenities.includes(a.key)
                      ? prev.amenities.filter((x) => x !== a.key)
                      : [...prev.amenities, a.key],
                  }))
                }
              >
                {a.label}
              </button>
            ))}
          </div>
        </div>
        <div className="stack">
          <button type="button" className="btn btn-primary" onClick={onClose}>
            Найти квартиру
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              reset();
              onClose();
            }}
          >
            Сбросить фильтры
          </button>
        </div>
      </div>
    </div>
  );
}
