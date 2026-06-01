import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/index.css";

const params = new URLSearchParams(window.location.search);
const uid = params.get("user_id");
if (uid) {
  document.cookie = `user_id=${encodeURIComponent(uid)}; path=/`;
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
