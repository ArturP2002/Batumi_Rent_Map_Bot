export type MapListing = {
  id: number;
  price_usd: number | string;
  lat: number;
  lon: number;
  rooms: string;
  district?: string;
  rent_type?: string;
  area_m2?: number | string | null;
  cover_url?: string | null;
};

export type ClusterMode = "far" | "mid" | "near";

export type ClusterVisual = "summary" | "count-pin" | "dot" | "pin" | "price" | "building";

export type MapCluster = {
  key: string;
  lat: number;
  lon: number;
  count: number;
  minPrice: number;
  items: MapListing[];
  rentType: "long_term" | "daily";
  visual: ClusterVisual;
  expandOnClick: boolean;
};

/** One physical point/building — coords stay fixed across zooms. */
type Building = {
  key: string;
  lat: number;
  lon: number;
  items: MapListing[];
  minPrice: number;
  rentType: "long_term" | "daily";
};

export function clusterModeForZoom(zoom: number): ClusterMode {
  if (zoom >= 15.4) return "near";
  if (zoom >= 13) return "mid";
  return "far";
}

/** Pixel merge radius — tighter as we zoom in. */
export function mergeRadiusPx(zoom: number): number {
  if (zoom >= 15.4) return 10; // only same building / almost identical
  if (zoom >= 14.2) return 36;
  if (zoom >= 13) return 44;
  if (zoom >= 12) return 52;
  return 60;
}

export function hasDetailFilters(f: {
  rooms: string[];
  amenities: string[];
  price_min?: number;
  price_max?: number;
  check_in?: string;
  check_out?: string;
}): boolean {
  return Boolean(
    f.rooms.length ||
      f.amenities.length ||
      f.price_min != null ||
      f.price_max != null ||
      f.check_in ||
      f.check_out,
  );
}

function majorityRentType(items: MapListing[]): "long_term" | "daily" {
  let daily = 0;
  for (const item of items) {
    if (item.rent_type === "daily") daily += 1;
  }
  return daily > items.length / 2 ? "daily" : "long_term";
}

function pickVisual(
  count: number,
  mode: ClusterMode,
  detailFilters: boolean,
): ClusterVisual {
  if (mode === "near") {
    return count > 1 ? "building" : "price";
  }
  if (mode === "far" || detailFilters) {
    return count > 1 ? "summary" : "dot";
  }
  return count > 1 ? "count-pin" : "pin";
}

/** Round to ~1.1 m so the same house always shares one stable key/position. */
function buildingKey(lat: number, lon: number): string {
  return `${lat.toFixed(5)}:${lon.toFixed(5)}`;
}

function groupBuildings(items: MapListing[]): Building[] {
  const buckets = new Map<string, MapListing[]>();
  for (const item of items) {
    if (!Number.isFinite(item.lat) || !Number.isFinite(item.lon)) continue;
    const key = buildingKey(item.lat, item.lon);
    const list = buckets.get(key);
    if (list) list.push(item);
    else buckets.set(key, [item]);
  }

  const buildings: Building[] = [];
  for (const [key, group] of buckets) {
    // Stable anchor: first listing by id — never a shifting average.
    const sorted = [...group].sort((a, b) => a.id - b.id);
    const anchor = sorted[0];
    const prices = sorted.map((i) => Number(i.price_usd)).filter(Number.isFinite);
    buildings.push({
      key,
      lat: anchor.lat,
      lon: anchor.lon,
      items: sorted,
      minPrice: prices.length ? Math.min(...prices) : 0,
      rentType: majorityRentType(sorted),
    });
  }
  return buildings.sort((a, b) => a.items[0].id - b.items[0].id);
}

type ProjectFn = (lon: number, lat: number) => { x: number; y: number };

/**
 * Cluster buildings in screen space. Marker lat/lon always equals a real
 * building anchor, so points don't drift when the zoom changes.
 */
export function buildClusters(
  items: MapListing[],
  zoom: number,
  detailFilters: boolean,
  project: ProjectFn,
): MapCluster[] {
  const mode = clusterModeForZoom(zoom);
  const buildings = groupBuildings(items);
  const radius = mergeRadiusPx(zoom);
  const r2 = radius * radius;

  type Acc = {
    buildings: Building[];
    x: number;
    y: number;
    anchor: Building;
  };

  const clusters: Acc[] = [];

  for (const building of buildings) {
    const p = project(building.lon, building.lat);
    let best: Acc | null = null;
    let bestDist = Infinity;

    for (const cluster of clusters) {
      const dx = p.x - cluster.x;
      const dy = p.y - cluster.y;
      const d2 = dx * dx + dy * dy;
      if (d2 <= r2 && d2 < bestDist) {
        best = cluster;
        bestDist = d2;
      }
    }

    if (best) {
      best.buildings.push(building);
      // Keep pixel center as the stable anchor's projection (no drifting mean).
      continue;
    }

    clusters.push({
      buildings: [building],
      x: p.x,
      y: p.y,
      anchor: building,
    });
  }

  return clusters.map((cluster) => {
    const allItems = cluster.buildings.flatMap((b) => b.items);
    const prices = allItems.map((i) => Number(i.price_usd)).filter(Number.isFinite);
    const count = allItems.length;
    const visual = pickVisual(count, mode, detailFilters);
    const anchor = cluster.anchor;
    return {
      key: cluster.buildings.map((b) => b.key).join("|"),
      lat: anchor.lat,
      lon: anchor.lon,
      count,
      minPrice: prices.length ? Math.min(...prices) : 0,
      items: allItems.sort((a, b) => a.id - b.id),
      rentType: majorityRentType(allItems),
      visual,
      expandOnClick: mode === "near" && count > 1,
    };
  });
}

export function formatUsd(value: number): string {
  return `$${Math.round(value).toLocaleString("en-US")}`;
}

export function clusterLabel(cluster: MapCluster): string {
  switch (cluster.visual) {
    case "summary":
    case "building":
      return cluster.count > 1
        ? `${cluster.count} от ${formatUsd(cluster.minPrice)}`
        : formatUsd(cluster.minPrice);
    case "count-pin":
      return String(cluster.count);
    case "price":
      return formatUsd(cluster.minPrice);
    case "dot":
    case "pin":
    default:
      return "";
  }
}
