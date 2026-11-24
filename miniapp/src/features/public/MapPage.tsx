import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { api, filtersToParams } from "@/shared/api";
import { useAuth } from "@/shared/auth";
import { roomLabel, useFilters } from "@/shared/filters";
import {
  buildClusters,
  clusterLabel,
  clusterModeForZoom,
  hasDetailFilters,
  type MapCluster,
  type MapListing,
} from "@/shared/mapClusters";
import { PropertyCardItem } from "@/shared/ui";
import { FiltersSheet } from "./FiltersSheet";

type Preview = {
  id: number;
  price_usd: number | string;
  rooms: string;
  district?: string | null;
  area_m2?: number | string | null;
  cover_url?: string | null;
  rent_type: string;
};

const BATUMI: [number, number] = [41.6367, 41.6168];
const FALLBACK_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

export function MapPage() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapObj = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);
  const listingsRef = useRef<MapListing[]>([]);
  const clusterSigRef = useRef("");
  const abortRef = useRef<AbortController | null>(null);
  const readyRef = useRef(false);
  const { filters, setFilters } = useFilters();
  const filtersRef = useRef(filters);
  const { isAdmin } = useAuth();
  const [showFilters, setShowFilters] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [selected, setSelected] = useState<MapListing | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [clusterList, setClusterList] = useState<MapCluster | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [markerCount, setMarkerCount] = useState(0);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const focusDone = useRef(false);

  filtersRef.current = filters;

  function clearDomMarkers() {
    for (const m of markersRef.current) m.remove();
    markersRef.current = [];
  }

  function openListing(item: MapListing) {
    setClusterList(null);
    setSelected(item);
  }

  function handleClusterClick(cluster: MapCluster) {
    const map = mapObj.current;
    if (!map) return;

    if (cluster.expandOnClick || (cluster.count > 1 && clusterModeForZoom(map.getZoom()) === "near")) {
      setSelected(null);
      setPreview(null);
      setClusterList(cluster);
      return;
    }

    if (cluster.count === 1) {
      openListing(cluster.items[0]);
      return;
    }

    // Zoom into cluster — points will split on next render
    const nextZoom = Math.min(map.getZoom() + 1.8, 17.5);
    map.easeTo({
      center: [cluster.lon, cluster.lat],
      zoom: nextZoom,
      duration: 420,
    });
  }

  function renderClusters(force = false) {
    const map = mapObj.current;
    if (!map || !readyRef.current) return;
    const zoom = map.getZoom();
    const detail = hasDetailFilters(filtersRef.current);
    const clusters = buildClusters(listingsRef.current, zoom, detail, (lon, lat) =>
      map.project([lon, lat]),
    );
    const sig = clusters
      .map((c) => `${c.key}@${c.lat.toFixed(5)},${c.lon.toFixed(5)}:${c.visual}:${c.count}:${c.minPrice}`)
      .sort()
      .join("|");
    if (!force && sig === clusterSigRef.current) return;
    clusterSigRef.current = sig;
    clearDomMarkers();

    for (const cluster of clusters) {
      // Root element is owned by MapLibre (inline transform). Visuals go inside.
      const root = document.createElement("button");
      root.type = "button";
      root.className = "map-marker-root";
      root.setAttribute(
        "aria-label",
        cluster.count > 1 ? `${cluster.count} объявлений` : "Объявление",
      );

      const body = document.createElement("span");
      const colorClass = cluster.rentType === "daily" ? "is-daily" : "is-long";
      body.className = `map-marker map-marker--${cluster.visual} ${colorClass}`;
      const label = clusterLabel(cluster);
      if (label) body.textContent = label;
      root.appendChild(body);

      root.addEventListener("click", (ev) => {
        ev.stopPropagation();
        handleClusterClick(cluster);
      });

      const marker = new maplibregl.Marker({ element: root, anchor: "bottom" })
        .setLngLat([cluster.lon, cluster.lat])
        .addTo(map);
      markersRef.current.push(marker);
    }
  }

  async function loadMarkers() {
    const map = mapObj.current;
    if (!map || !readyRef.current) return;
    map.resize();
    setLoading(true);
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    const current = filtersRef.current;
    try {
      const qs = filtersToParams(current);
      const items = await api<MapListing[]>(`/api/public/map/markers?${qs}`, {
        signal: ac.signal,
      });
      listingsRef.current = items;
      setMarkerCount(items.length);
      setError(items.length ? null : "В этой зоне пока нет объявлений");
      renderClusters(true);
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setError("Не удалось загрузить метки");
        setMarkerCount(0);
        listingsRef.current = [];
        clusterSigRef.current = "";
        clearDomMarkers();
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    if (!mapRef.current || mapObj.current) return;
    let cancelled = false;
    const container = mapRef.current;

    const map = new maplibregl.Map({
      container,
      style: "https://tiles.openfreemap.org/styles/liberty",
      center: BATUMI,
      zoom: 12.2,
      attributionControl: false,
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.AttributionControl({ compact: true }));
    mapObj.current = map;

    const onReady = () => {
      if (cancelled) return;
      readyRef.current = true;
      map.resize();
      void loadMarkers();
    };

    const onViewChange = () => {
      if (!readyRef.current || !listingsRef.current.length) return;
      renderClusters();
    };

    map.on("load", onReady);
    map.on("zoomend", onViewChange);
    map.on("error", (e) => {
      console.warn("map error", e);
      if (!readyRef.current) {
        map.setStyle(FALLBACK_STYLE);
      }
    });

    const ro =
      typeof ResizeObserver !== "undefined"
        ? new ResizeObserver(() => {
            map.resize();
          })
        : null;
    ro?.observe(container);

    if (map.loaded()) onReady();

    return () => {
      cancelled = true;
      readyRef.current = false;
      ro?.disconnect();
      clearDomMarkers();
      map.remove();
      mapObj.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    void loadMarkers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  useEffect(() => {
    const lat = Number(searchParams.get("lat"));
    const lon = Number(searchParams.get("lon"));
    const focusId = searchParams.get("id");
    const map = mapObj.current;
    if (!map || focusDone.current) return;
    if (Number.isFinite(lat) && Number.isFinite(lon) && lat && lon) {
      map.flyTo({ center: [lon, lat], zoom: 16 });
      if (focusId) {
        setSelected({
          id: Number(focusId),
          price_usd: 0,
          lat,
          lon,
          rooms: "",
          rent_type: filters.rent_type,
        });
      }
      focusDone.current = true;
    }
  }, [searchParams, loading, filters.rent_type]);

  useEffect(() => {
    if (!selected) {
      setPreview(null);
      return;
    }
    let cancelled = false;
    setPreview({
      id: selected.id,
      price_usd: selected.price_usd,
      rooms: selected.rooms,
      district: selected.district,
      area_m2: selected.area_m2 ?? null,
      rent_type: selected.rent_type || filters.rent_type,
      cover_url: selected.cover_url || null,
    });
    void (async () => {
      try {
        const detail = await api<{
          id: number;
          price_usd: number;
          rooms: string;
          district?: string | null;
          area_m2?: number | null;
          rent_type: string;
          photos?: { url: string; thumb_url?: string }[];
          cover_url?: string | null;
        }>(`/api/public/properties/${selected.id}`);
        if (cancelled) return;
        setPreview({
          id: detail.id,
          price_usd: detail.price_usd,
          rooms: detail.rooms,
          district: detail.district,
          area_m2: detail.area_m2,
          rent_type: detail.rent_type,
          cover_url:
            detail.cover_url ||
            detail.photos?.[0]?.thumb_url ||
            detail.photos?.[0]?.url ||
            null,
        });
      } catch {
        /* keep lightweight marker preview */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selected, filters.rent_type]);

  const period = (preview?.rent_type || filters.rent_type) === "daily" ? "/сутки" : "/мес";

  return (
    <div className="page-map-full">
      <div className="map-stage">
        <div className="map-canvas" ref={mapRef} />
      </div>

      <div className="map-top">
        <div className="map-brand">
          <span className="map-brand-mark" aria-hidden />
          <strong>Batumi Rent</strong>
        </div>
        <div className="map-controls">
          <button
            type="button"
            className={`chip ${filters.rent_type === "long_term" ? "active" : ""}`}
            onClick={() => setFilters((p) => ({ ...p, rent_type: "long_term" }))}
          >
            Долгосрочно
          </button>
          <button
            type="button"
            className={`chip chip-daily ${filters.rent_type === "daily" ? "active" : ""}`}
            onClick={() => setFilters((p) => ({ ...p, rent_type: "daily" }))}
          >
            Посуточно
          </button>
          <button type="button" className="chip" onClick={() => setShowFilters(true)}>
            Фильтры
          </button>
          <Link className="chip" to="/list">
            Список
          </Link>
          <button type="button" className="chip" onClick={() => setShowMenu(true)}>
            Меню
          </button>
        </div>
        {loading && <div className="map-status is-loading">Обновляем карту…</div>}
        {!loading && markerCount > 0 && (
          <div className="map-status">{markerCount} на карте · масштабируйте для деталей</div>
        )}
        {error && (
          <div className="map-status" style={{ background: "rgba(220,38,38,.85)" }}>
            {error}
          </div>
        )}
      </div>

      <div className="map-dock">
        {preview && !clusterList && (
          <article className="map-pick" style={{ position: "relative" }}>
            <button
              type="button"
              className="map-pick-close"
              aria-label="Закрыть"
              onClick={() => {
                setSelected(null);
                setPreview(null);
              }}
            >
              ×
            </button>
            <img src={preview.cover_url || ""} alt="" />
            <div className="map-pick-body">
              <div>
                <div className="price">
                  ${preview.price_usd || "—"}
                  <span className="muted" style={{ fontFamily: "var(--font-ui)", fontSize: 13 }}>
                    {period}
                  </span>
                </div>
                <div className="muted">
                  {roomLabel(preview.rooms)}
                  {preview.area_m2 ? ` · ${preview.area_m2} м²` : ""}
                </div>
                <div className="muted">{preview.district || "Батуми"}</div>
              </div>
              <div className="map-pick-actions">
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => navigate(`/property/${preview.id}`)}
                >
                  Смотреть
                </button>
              </div>
            </div>
          </article>
        )}
      </div>

      {clusterList && (
        <div
          className="sheet-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setClusterList(null);
          }}
        >
          <div className="sheet" role="dialog" aria-modal="true" aria-label="Объявления в точке">
            <div className="sheet-handle" />
            <h3 style={{ marginTop: 0 }}>
              {clusterList.count} объявл. · от ${Math.round(clusterList.minPrice)}
            </h3>
            <p className="muted" style={{ marginTop: -6 }}>
              В этом доме / точке на карте
            </p>
            <div className="list-grid" style={{ marginTop: 12 }}>
              {clusterList.items.map((item) => (
                <PropertyCardItem
                  key={item.id}
                  item={{
                    id: item.id,
                    price_usd: item.price_usd,
                    rooms: item.rooms,
                    district: item.district,
                    area_m2: item.area_m2,
                    cover_url: item.cover_url,
                    rent_type: item.rent_type || filters.rent_type,
                  }}
                  onOpen={() => {
                    setClusterList(null);
                    navigate(`/property/${item.id}`);
                  }}
                />
              ))}
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-block"
              style={{ marginTop: 12 }}
              onClick={() => setClusterList(null)}
            >
              Закрыть
            </button>
          </div>
        </div>
      )}

      {showFilters && <FiltersSheet onClose={() => setShowFilters(false)} />}

      {showMenu && (
        <div
          className="sheet-backdrop"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowMenu(false);
          }}
        >
          <div className="sheet menu-sheet" role="dialog" aria-label="Меню">
            <div className="sheet-handle" />
            <h3 style={{ marginTop: 0, fontFamily: "var(--font-display)" }}>Меню</h3>
            <div className="stack">
              <Link className="btn btn-secondary btn-block" to="/favorites" onClick={() => setShowMenu(false)}>
                Избранное
              </Link>
              <Link className="btn btn-secondary btn-block" to="/help" onClick={() => setShowMenu(false)}>
                Помощь
              </Link>
              {isAdmin && (
                <Link className="btn btn-secondary btn-block" to="/admin" onClick={() => setShowMenu(false)}>
                  Админ-панель
                </Link>
              )}
              <button
                type="button"
                className="btn btn-ghost btn-block"
                onClick={() => {
                  mapObj.current?.flyTo({ center: BATUMI, zoom: 12.2 });
                  setShowMenu(false);
                }}
              >
                Сбросить карту на Батуми
              </button>
              <button type="button" className="btn btn-secondary btn-block" onClick={() => setShowMenu(false)}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
