import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, registerSessionRefresh, setToken } from "./api";

type Me = {
  id: number;
  telegram_id: number;
  username?: string;
  first_name?: string;
  roles: string[];
  realtor_id?: number | null;
};

type AuthCtx = {
  me: Me | null;
  loading: boolean;
  isAdmin: boolean;
  refresh: () => Promise<void>;
};

const Ctx = createContext<AuthCtx>({
  me: null,
  loading: true,
  isAdmin: false,
  refresh: async () => undefined,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const initData = window.Telegram?.WebApp?.initData;
      if (initData) {
        // Avoid recursive 401 loop: call fetch directly for session
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        headers["X-Telegram-Init-Data"] = initData;
        const base = import.meta.env.VITE_API_URL || "";
        const res = await fetch(`${base}/api/public/auth/session`, {
          method: "POST",
          headers,
          body: JSON.stringify({ initData }),
        });
        if (res.ok) {
          const session = (await res.json()) as { token: string };
          setToken(session.token);
        }
      }
      const profile = await api<Me>("/api/public/me");
      setMe(profile);
    } catch {
      setMe(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    registerSessionRefresh(refresh);
    window.Telegram?.WebApp?.ready();
    window.Telegram?.WebApp?.expand();
    void refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({
      me,
      loading,
      isAdmin: !!me?.roles.includes("admin"),
      refresh,
    }),
    [me, loading, refresh],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  return useContext(Ctx);
}
