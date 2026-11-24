import { Link, Navigate, NavLink, Outlet } from "react-router-dom";
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
  const { isAdmin, loading } = useAuth();
  if (loading) return <StateBox title="Проверяем доступ…" />;
  if (!isAdmin) return <Navigate to="/map" replace />;

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
