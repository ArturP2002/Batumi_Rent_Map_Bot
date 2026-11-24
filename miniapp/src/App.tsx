import { BrowserRouter, useLocation } from "react-router-dom";
import { AuthProvider } from "@/shared/auth";
import { FiltersProvider } from "@/shared/filters";
import { AppRouter } from "@/app/router";

function Shell() {
  const { pathname } = useLocation();
  const isAdmin = pathname.startsWith("/admin");
  const isMap = pathname.startsWith("/map");
  const isWide = isMap || pathname.startsWith("/list");
  const className = [
    "app-shell",
    isMap ? "is-map" : "",
    isAdmin ? "is-admin" : "",
    isWide && !isMap ? "is-wide" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <AppRouter />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <FiltersProvider>
          <Shell />
        </FiltersProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}
