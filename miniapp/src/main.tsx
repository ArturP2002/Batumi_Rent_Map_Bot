import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { initTelegramApp } from "./shared/telegram";
import "./styles/global.css";
import "./styles/modern-blue-map.css";

initTelegramApp();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
