const API_BASE = import.meta.env.VITE_API_URL || "";

let sessionToken: string | null = localStorage.getItem("brm_token");
let refreshSession: (() => Promise<void>) | null = null;

export function setToken(token: string | null) {
  sessionToken = token;
  if (token) localStorage.setItem("brm_token", token);
  else localStorage.removeItem("brm_token");
}

export function getToken() {
  return sessionToken;
}

export function getApiBase() {
  return API_BASE;
}

export function registerSessionRefresh(fn: () => Promise<void>) {
  refreshSession = fn;
}

export type FiltersState = {
  rent_type: "long_term" | "daily";
  rooms: string[];
  price_min?: number;
  price_max?: number;
  amenities: string[];
  check_in?: string;
  check_out?: string;
  sort?: string;
};

export function filtersToParams(f: FiltersState, extra?: Record<string, string>) {
  const p = new URLSearchParams();
  p.set("rent_type", f.rent_type);
  f.rooms.forEach((r) => p.append("rooms", r));
  f.amenities.forEach((a) => p.append("amenities", a));
  if (f.price_min != null) p.set("price_min", String(f.price_min));
  if (f.price_max != null) p.set("price_max", String(f.price_max));
  if (f.check_in) p.set("check_in", f.check_in);
  if (f.check_out) p.set("check_out", f.check_out);
  if (f.sort) p.set("sort", f.sort);
  if (extra) Object.entries(extra).forEach(([k, v]) => p.set(k, v));
  return p;
}

function buildHeaders(options: RequestInit): Headers {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (sessionToken) headers.set("Authorization", `Bearer ${sessionToken}`);
  const initData = window.Telegram?.WebApp?.initData;
  if (initData) headers.set("X-Telegram-Init-Data", initData);
  return headers;
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  _retried = false,
): Promise<T> {
  const headers = buildHeaders(options);
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401 && !_retried && window.Telegram?.WebApp?.initData && refreshSession) {
    setToken(null);
    try {
      await refreshSession();
      return api<T>(path, options, true);
    } catch {
      /* fall through */
    }
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res as unknown as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const headers = buildHeaders({});
  const res = await fetch(`${API_BASE}${path}`, { headers });
  if (!res.ok) throw new Error(await res.text());
  return res.blob();
}
