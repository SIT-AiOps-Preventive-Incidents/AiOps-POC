export const number = (
  value: number | string | null | undefined,
  digits = 1,
) => (value == null || value === "" ? "—" : Number(value).toFixed(digits));
export const percent = (value: number | null | undefined, digits = 1) =>
  value == null ? "—" : `${(value * 100).toFixed(digits)}%`;
export const metricPercent = (value: number | null | undefined) =>
  value == null ? "—" : `${Math.round(value)}%`;
export const milliseconds = (value: number | null | undefined) =>
  value == null
    ? "—"
    : value >= 1000
      ? `${(value / 1000).toFixed(2)} s`
      : `${Math.round(value)} ms`;
export const duration = (seconds: number | null | undefined) => {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600)
    return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  return `${(seconds / 3600).toFixed(1)}h`;
};
export const ago = (timestamp: number | null | undefined) => {
  if (!timestamp) return "—";
  const seconds = Date.now() / 1000 - timestamp;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} hr ago`;
  return `${Math.round(seconds / 86400)} days ago`;
};
export const time = (timestamp: number | null | undefined) =>
  timestamp
    ? new Date(timestamp * 1000).toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
export const titleCase = (value: string) =>
  value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
export const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "Something went wrong";
