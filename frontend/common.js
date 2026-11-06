// Laptop par (Live Server, port 5500) backend 127.0.0.1:5000 par hai,
// baaki har jagah (Flask ya online website) same server use karo.
const API_BASE = location.port === "5500" || location.protocol === "file:" ? "http://127.0.0.1:5000" : "";

// Har browser/phone ki apni random ID, taaki sabki history alag rahe
function getClientId() {
  let id = localStorage.getItem("truthlens_client_id");
  if (!id) {
    id = (crypto.randomUUID && crypto.randomUUID()) ||
      Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 12);
    localStorage.setItem("truthlens_client_id", id);
  }
  return id;
}

function api(path, options = {}) {
  options.headers = { ...(options.headers || {}), "X-Client-Id": getClientId() };
  return fetch(API_BASE + path, options);
}
