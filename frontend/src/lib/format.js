// Formatting helpers shared by every view. Pure functions, no Vue.

export const pct = (v, d = 1) => (v == null ? "-" : `${(v * 100).toFixed(d)}%`);
export const num = (v, d = 1) => (v == null ? "-" : Number(v).toFixed(d));
export const ms = (v) => (v == null ? "-" : v >= 1000 ? `${(v / 1000).toFixed(2)} s` : `${Math.round(v)} ms`);
export const round = (v) => (v == null ? "-" : `${Math.round(v)}%`);

export function ago(ts) {
  if (!ts) return "-";
  const s = Date.now() / 1000 - ts;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export function dur(s) {
  if (s == null || Number.isNaN(s)) return "-";
  if (s < 60) return `${Math.round(s)} s`;
  if (s < 3600) return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`;
  return `${(s / 3600).toFixed(1)} h`;
}

export const clock = (ts) => (ts ? new Date(ts * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "");
export const clockSec = (ts) => (ts ? new Date(ts * 1000).toLocaleTimeString() : "-");
export const slug = (v) => v.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9._-]/g, "");
