// Where the app is served from. Directly on the VM that is "/", behind the faculty's proxy it is "/capstone26/cp26pt1/".
// The routes live in the hash, so the page's own path never changes while the app runs.
// Several slashes become one: "//host/" would otherwise send our calls, and passwords, to another host.
export const basePath = (pathname) => `/${pathname}`.replace(/[^/]*$/, "").replace(/\/{2,}/g, "/");

export const BASE = typeof window === "undefined" ? "/" : basePath(window.location.pathname);

export const at = (path, base = BASE) => base + path.replace(/^\/+/, "");

// the same, with the host in front: for commands a person copies
export const appUrl = () => window.location.origin + BASE.replace(/\/$/, "");
