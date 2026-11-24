import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "@/shared/auth";
import { StateBox } from "@/shared/ui";
import "./AdminModernBlue.css";

const navigation = [
  { to: "/admin", label: "Обзор", icon: "▦", end: true },
  { to: "/admin/listings", label: "Объявления", icon: "⌂" },
  { to: "/admin/realtors", label: "Риелторы", icon: "♙" },
  { to: "/admin/deals", label: "Сделки", icon: "◇" },
  { to: "/admin/reviews", label: "Отзывы", icon: "☆" },
  { to: "/admin/stats", label: "Аналитика", icon: "▥" },
  { to: "/admin/settings", label: "Настройки", icon: "⚙" },
];

export function AdminLayout() {
  const { isAdmin, loading, refresh } = useAuth();
  if (loading) return <StateBox title="Проверяем доступ…" />;
  if (!isAdmin) {
    return (
      <div className="mba-shell" style={{ padding: 24 }}>
        <StateBox title="Нет доступа к админ-панели" />
        <p style={{ textAlign: "center", color: "#75869b", marginTop: 8 }}>
          Войдите через Telegram под аккаунтом администратора.
        </p>
        <div style={{ display: "grid", gap: 10, maxWidth: 360, margin: "18px auto 0" }}>
          <button type="button" className="mba-nav-item" onClick={() => void refresh()}>
            Повторить проверку
          </button>
          <Link to="/map" className="mba-nav-item">
            ← На карту
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mba-shell">
      <div className="mba-topbar">
        <Link to="/map" className="mba-back" aria-label="Вернуться к карте">←</Link>
        <div className="mba-brand"><span className="mba-brand-symbol">⌖</span><span>batumi <strong>rent</strong><small>ПАНЕЛЬ УПРАВЛЕНИЯ</small></span></div>
        <div className="mba-admin-indicator"><span /> Администратор</div>
      </div>
      <div className="mba-workspace">
        <aside className="mba-sidebar">
          <div className="mba-nav-caption">УПРАВЛЕНИЕ</div>
          <nav className="mba-navigation" aria-label="Разделы администрирования">
            {navigation.map(item => <NavLink key={item.to} to={item.to} end={item.end} className={({isActive}) => `mba-nav-item ${isActive ? "is-active" : ""}`}>
              <span className="mba-nav-icon" aria-hidden="true">{item.icon}</span><span>{item.label}</span>
            </NavLink>)}
          </nav>
          <div className="mba-sidebar-foot"><span className="mba-live" /> Панель Batumi Rent Map</div>
        </aside>
        <main className="mba-main"><Outlet /></main>
      </div>
    </div>
  );
}
