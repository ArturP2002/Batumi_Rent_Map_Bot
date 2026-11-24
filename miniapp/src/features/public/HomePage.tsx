import { Navigate } from "react-router-dom";

/** Map-first: home is just an entry redirect into search. */
export function HomePage() {
  return <Navigate to="/map" replace />;
}
