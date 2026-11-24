import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/shared/auth";
import { StateBox } from "@/shared/ui";

const tabs = [
  { to: "/admin", label: "Дашборд", end: true },
  { to: "/admin/listings", label: "Объявления" },
  { to: "/admin/realtors", label: "Риелторы" },
  { to: "/admin/deals", label: "Сделки" },
  { to: "/admin/reviews", label: "Отзывы" },
  { to: "/admin/stats", label: "Статистика" },
  { to: "/admin/settings", label: "Настройки" },
];

export function AdminLayout() {
  const { isAdmin, loading } = useAuth();
  const loc = useLocation();

  if (loading) return <StateBox title="Проверка доступа…" />;
  if (!isAdmin) return <Navigate to="/" replace />;

  return (
    <div className="page">
      <div className="toolbar">
        <Link className="chip" to="/map">
          ← Карта
        </Link>
        <strong>Админ</strong>
      </div>
      <div className="admin-layout">
        <nav className="admin-nav tabs" aria-label="Админ-разделы">
          {tabs.map((t) => {
            const active = t.end ? loc.pathname === t.to : loc.pathname.startsWith(t.to);
            return (
              <Link key={t.to} to={t.to} className={active ? "active" : ""}>
                {t.label}
              </Link>
            );
          })}
        </nav>
        <div className="admin-content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
