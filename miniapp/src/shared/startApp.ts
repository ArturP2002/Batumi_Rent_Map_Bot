/** Resolve Telegram Mini App start parameter from several possible sources. */
export function parseStartApp(): string | null {
  const fromTg = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
  if (fromTg) return fromTg;

  const url = new URL(window.location.href);
  const fromQuery = url.searchParams.get("startapp") || url.searchParams.get("tgWebAppStartParam");
  if (fromQuery) return fromQuery;

  // Telegram sometimes puts params into the hash: #tgWebAppStartParam=admin&...
  const hash = url.hash.startsWith("#") ? url.hash.slice(1) : url.hash;
  if (hash) {
    const hp = new URLSearchParams(hash);
    const fromHash = hp.get("tgWebAppStartParam") || hp.get("startapp");
    if (fromHash) return fromHash;
  }
  return null;
}

/** Map startapp value → in-app path. */
export function pathForStartApp(param: string | null | undefined): string | null {
  if (!param) return null;
  if (param.startsWith("property_")) return `/property/${param.slice(9)}`;
  if (param.startsWith("realtor_")) return `/realtor/${param.slice(8)}`;
  if (param.startsWith("deal_")) return `/deal/${param.slice(5)}`;
  if (param === "favorites") return "/favorites";
  if (param === "admin") return "/admin";
  if (param === "admin_listings") return "/admin/listings";
  if (param === "admin_deals") return "/admin/deals";
  if (param === "admin_reviews") return "/admin/reviews";
  if (param === "list") return "/list";
  if (param === "map") return "/map";
  return null;
}
