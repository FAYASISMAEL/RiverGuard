// Same-origin production requests preserve admin cookies and avoid CORS drift.
export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ||
  (import.meta.env.VITE_API_URL
    ? import.meta.env.VITE_API_URL.replace(/\/$/, "") + "/api"
    : "/api")
).replace(/\/$/, "");
const assetOrigin = /^https?:\/\//.test(API_BASE)
  ? new URL(API_BASE).origin
  : "";
let csrfToken = "";
export const setCsrfToken = (value) => {
  csrfToken = value;
};
export const assetUrl = (path) =>
  /^https?:\/\//.test(path) ? path : assetOrigin + path;
export const localDay = (value) => {
  const d = new Date(/Z$|[+-]\d{2}:\d{2}$/.test(value) ? value : value + "Z");
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
export async function api(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    ...options,
    credentials: "include",
    signal: options.signal || AbortSignal.timeout(20000),
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}),
      ...options.headers,
    },
  }).catch(() => {
    throw new Error(
      "Could not reach the server. Check your connection. If you were submitting, check the map before retrying to avoid duplicates.",
    );
  });
  const data = await response.json().catch(() => null);
  if (response.status === 401 && path !== "/admin/login")
    window.dispatchEvent(new Event("admin-session-expired"));
  if (!response.ok || data === null) {
    const detail =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? data.detail.map((x) => x.msg).join("; ")
          : "";
    if (detail) throw new Error(detail);
    if (
      response.status === 404 ||
      response.status === 405 ||
      (response.ok && data === null)
    )
      throw new Error(
        "The API route is unavailable. Check the deployment's root directory and API routing, then redeploy.",
      );
    if (response.status >= 500)
      throw new Error(
        `The backend is unavailable (HTTP ${response.status}). Check the server logs and database configuration, then try again.`,
      );
    if (response.status === 413)
      throw new Error(
        "This photo exceeds the server's upload limit. Choose a smaller image.",
      );
    throw new Error(
      `The request failed (HTTP ${response.status}). Please try again.`,
    );
  }
  return data;
}
export async function mapApi(path) {
  // Map reads are safe to retry. Never automatically retry uploads or mutations.
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      return await api(path);
    } catch (error) {
      if (attempt === 2) throw error;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }
}
export const post = (path, data) =>
  api(path, { method: "POST", body: JSON.stringify(data) });
export const patch = (path, data) =>
  api(path, { method: "PATCH", body: JSON.stringify(data) });
export const categories = [
  "Industrial Discharge",
  "Sewage",
  "Oil / Fuel",
  "Plastic / Solid Waste",
  "Agricultural Runoff",
  "Dead Fish",
  "Water Discoloration",
  "Foam",
  "Bad Odour",
  "Other / Unclear",
  "Other",
];
export const dateLabel = (value) =>
  new Date(
    value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : value + "Z",
  ).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
