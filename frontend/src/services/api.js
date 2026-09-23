const base = import.meta.env.VITE_API_URL || "";
export const assetUrl = (path) => base + path;
export async function api(path, options = {}) {
  const response = await fetch(base + "/api" + path, {
    ...options,
    signal: options.signal || AbortSignal.timeout(20000),
    headers: {
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...(sessionStorage.getItem("authorityKey")
        ? { "X-Authority-Key": sessionStorage.getItem("authorityKey") }
        : {}),
      ...options.headers,
    },
  }).catch(() => {
    throw new Error(
      "Could not reach the server. Check your connection. If you were submitting, check the map before retrying to avoid duplicates.",
    );
  });
  const data = await response.json().catch(() => null);
  if (!response.ok)
    throw new Error(
      typeof data?.detail === "string"
        ? data.detail
        : data?.detail?.map((x) => x.msg).join("; ") ||
            "The server could not complete this request. Please try again.",
    );
  return data;
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
  "Other",
];
export const dateLabel = (value) =>
  new Date(
    value.endsWith("Z") || /[+-]\d\d:\d\d$/.test(value) ? value : value + "Z",
  ).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
