import { Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { useEffect } from "react";
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

function parseStartApp(): string | null {
  const fromTg = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
  if (fromTg) return fromTg;
  const url = new URL(window.location.href);
  return url.searchParams.get("startapp");
}

function StartAppRedirect() {
  const navigate = useNavigate();
  useEffect(() => {
    const param = parseStartApp();
    if (!param) return;
    if (param.startsWith("property_")) navigate(`/property/${param.slice(9)}`, { replace: true });
    else if (param.startsWith("realtor_")) navigate(`/realtor/${param.slice(8)}`, { replace: true });
    else if (param.startsWith("deal_")) navigate(`/deal/${param.slice(5)}`, { replace: true });
    else if (param === "favorites") navigate("/favorites", { replace: true });
    else if (param === "admin") navigate("/admin", { replace: true });
    else if (param === "admin_listings") navigate("/admin/listings", { replace: true });
    else if (param === "admin_deals") navigate("/admin/deals", { replace: true });
    else if (param === "admin_reviews") navigate("/admin/reviews", { replace: true });
  }, [navigate]);
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
