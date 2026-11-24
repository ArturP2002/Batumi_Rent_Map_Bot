import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { FiltersState } from "./api";

const defaultFilters: FiltersState = {
  rent_type: "long_term",
  rooms: [],
  amenities: [],
  sort: "newest",
};

type FiltersCtx = {
  filters: FiltersState;
  setFilters: (f: FiltersState | ((prev: FiltersState) => FiltersState)) => void;
  reset: () => void;
};

const Ctx = createContext<FiltersCtx | null>(null);

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<FiltersState>(defaultFilters);
  const value = useMemo(
    () => ({
      filters,
      setFilters,
      reset: () => setFilters(defaultFilters),
    }),
    [filters],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useFilters() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("FiltersProvider missing");
  return ctx;
}

export const AMENITIES = [
  { key: "wifi", label: "Wi‑Fi" },
  { key: "air_conditioning", label: "Кондиционер" },
  { key: "kitchen", label: "Кухня" },
  { key: "oven", label: "Духовка" },
  { key: "microwave", label: "Микроволновка" },
  { key: "parking", label: "Парковка" },
  { key: "furniture", label: "Мебель" },
  { key: "dishwasher", label: "Посудомойка" },
  { key: "sea_view", label: "Вид на море" },
  { key: "bedrooms_with_windows", label: "Спальни с окнами" },
  { key: "washing_machine", label: "Стиралка" },
  { key: "balcony", label: "Балкон" },
  { key: "elevator", label: "Лифт" },
  { key: "central_heating", label: "Центр. отопление" },
  { key: "hot_water", label: "Горячая вода" },
  { key: "pets_allowed", label: "С животными" },
  { key: "tv", label: "ТВ" },
  { key: "mountain_view", label: "Вид на горы" },
];

export const ROOM_OPTIONS = ["studio", "1", "2", "3", "4+"] as const;

export type RoomOption = (typeof ROOM_OPTIONS)[number];

const ROOM_LABELS: Record<string, string> = {
  studio: "Студия",
  "1": "1",
  "2": "2",
  "3": "3",
  "4+": "4+",
};

export function roomLabel(rooms: string | null | undefined): string {
  if (!rooms) return "—";
  return ROOM_LABELS[rooms] || rooms;
}
