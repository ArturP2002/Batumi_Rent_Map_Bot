import { Navigate } from "react-router-dom";
import { parseStartApp, pathForStartApp } from "@/shared/startApp";

/** Entry route: honour Telegram startapp, otherwise open the map. */
export function HomePage() {
  const target = pathForStartApp(parseStartApp()) || "/map";
  return <Navigate to={target} replace />;
}
