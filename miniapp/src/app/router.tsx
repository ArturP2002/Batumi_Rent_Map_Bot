import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef } from "react";
import { HomePage } from "@/features/public/HomePage";
import { MapPage } from "@/features/public/MapPage";
import { ListPage } from "@/features/public/ListPage";
import { PropertyPage } from "@/features/public/PropertyPage";
import { FavoritesPage } from "@/features/public/FavoritesPage";
import { RealtorPage } from "@/features/public/RealtorPage";
import { HelpPage } from "@/features/public/HelpPage";
import { ReviewPage } from "@/features/public/ReviewPage";
import { DealConfirmPage } from "@/features/public/DealConfirmPage";
import { AdminLayout } from "@/features/admin/AdminLayout";
import { DashboardPage } from "@/features/admin/DashboardPage";
import { ListingsPage } from "@/features/admin/ListingsPage";
import { RealtorsPage } from "@/features/admin/RealtorsPage";
import { DealsPage } from "@/features/admin/DealsPage";
import { ReviewsPage } from "@/features/admin/ReviewsPage";
import { StatsPage } from "@/features/admin/StatsPage";
import { SettingsPage } from "@/features/admin/SettingsPage";
import { parseStartApp, pathForStartApp } from "@/shared/startApp";

/** Apply Telegram startapp deep-links (with a short retry — initData can arrive late). */
function StartAppRedirect() {
  const navigate = useNavigate();
  const location = useLocation();
  const applied = useRef(false);

  useEffect(() => {
    if (applied.current) return;

    const tryApply = () => {
      if (applied.current) return;
      const target = pathForStartApp(parseStartApp());
      if (!target) return;
      applied.current = true;
      if (location.pathname !== target) {
        navigate(target, { replace: true });
      }
    };

    tryApply();
    const t1 = window.setTimeout(tryApply, 50);
    const t2 = window.setTimeout(tryApply, 300);
    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
    };
  }, [navigate, location.pathname]);

  return null;
}

export function AppRouter() {
  return (
    <>
      <StartAppRedirect />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/map" element={<MapPage />} />
        <Route path="/list" element={<ListPage />} />
        <Route path="/property/:id" element={<PropertyPage />} />
        <Route path="/favorites" element={<FavoritesPage />} />
        <Route path="/realtor/:id" element={<RealtorPage />} />
        <Route path="/help" element={<HelpPage />} />
        <Route path="/review" element={<ReviewPage />} />
        <Route path="/deal/:id" element={<DealConfirmPage />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="listings" element={<ListingsPage />} />
          <Route path="realtors" element={<RealtorsPage />} />
          <Route path="deals" element={<DealsPage />} />
          <Route path="reviews" element={<ReviewsPage />} />
          <Route path="stats" element={<StatsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/map" replace />} />
      </Routes>
    </>
  );
}
