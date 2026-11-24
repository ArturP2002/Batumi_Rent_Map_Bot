import type { ReactNode } from "react";
import { roomLabel } from "@/shared/filters";

export function StateBox({
  title,
  children,
  loading = /загруз|проверк|считаем/i.test(title),
}: {
  title: string;
  children?: ReactNode;
  loading?: boolean;
}) {
  return (
    <div className="state-box">
      {loading && <div className="state-spinner" aria-hidden />}
      <div>{title}</div>
      {children}
    </div>
  );
}

export function HeartIcon({ filled }: { filled: boolean }) {
  return (
    <svg
      className={`heart-icon ${filled ? "is-filled" : "is-empty"}`}
      viewBox="0 0 24 24"
      width="20"
      height="20"
      aria-hidden
      focusable="false"
    >
      <path
        d="M12 5.85c-1.55-1.7-4.05-2.1-5.95-.7-2.25 1.65-2.45 4.85-.45 6.85L12 18.5l6.4-6.5c2-2 1.8-5.2-.45-6.85-1.9-1.4-4.4-1-5.95.7z"
        fill={filled ? "currentColor" : "none"}
        stroke="currentColor"
        strokeWidth={filled ? 0 : 1.75}
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function PropertyCardItem({
  item,
  onOpen,
  onFavorite,
}: {
  item: {
    id: number;
    cover_url?: string | null;
    price_usd: number | string;
    rooms: string;
    area_m2?: number | string | null;
    district?: string | null;
    address?: string | null;
    is_favorite?: boolean;
    rent_type: string;
  };
  onOpen: () => void;
  onFavorite?: () => void;
}) {
  const period = item.rent_type === "daily" ? "/сутки" : "/мес";
  return (
    <article className="card card-row" onClick={onOpen} role="button">
      <img src={item.cover_url || ""} alt="" />
      <div>
        <div className="price">
          ${item.price_usd}
          <span className="muted"> {period}</span>
        </div>
        <div className="muted">
          {roomLabel(item.rooms)} · {item.area_m2 ? `${item.area_m2} м²` : "—"}
        </div>
        <div className="muted">{item.district || item.address || "Батуми"}</div>
      </div>
      {onFavorite && (
        <button
          type="button"
          className={`chip chip-fav ${item.is_favorite ? "is-on" : ""}`}
          aria-label={item.is_favorite ? "Убрать из избранного" : "В избранное"}
          aria-pressed={Boolean(item.is_favorite)}
          onClick={(e) => {
            e.stopPropagation();
            onFavorite();
          }}
        >
          <HeartIcon filled={Boolean(item.is_favorite)} />
        </button>
      )}
    </article>
  );
}

export function FilterBar({
  rentType,
  onRentType,
  onOpenFilters,
  resultCount,
}: {
  rentType: string;
  onRentType: (v: "long_term" | "daily") => void;
  onOpenFilters: () => void;
  resultCount?: number;
}) {
  return (
    <div className="filter-bar">
      <button
        type="button"
        className={`chip ${rentType === "long_term" ? "active" : ""}`}
        onClick={() => onRentType("long_term")}
      >
        Долгосрочно
      </button>
      <button
        type="button"
        className={`chip ${rentType === "daily" ? "active" : ""}`}
        onClick={() => onRentType("daily")}
      >
        Посуточно
      </button>
      <button type="button" className="chip" onClick={onOpenFilters}>
        Фильтры
      </button>
      {resultCount != null && <span className="muted">{resultCount} найдено</span>}
    </div>
  );
}
