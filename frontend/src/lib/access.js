// Who may do what, on the client: the signed-in person's permissions (from /auth/me) and the editing rules of the
// permission matrix. The server checks every call anyway (app/rbac.py); this only decides what to show.

export const can = (me, perm) => !!me && (me.role === "admin" || (me.permissions || []).includes("admin") || (me.permissions || []).includes(perm));

export function groupSpans(permissions, groups) {
  return groups.map((group) => ({ group, span: permissions.filter((p) => p.group === group).length })).filter((g) => g.span);
}

// admin's row and everyone's "read" are locked on: without them nobody could fix a mistake, or open the app
export function toggleCell(matrix, role, perm) {
  if (role === "admin" || perm === "read") return matrix;
  const cur = matrix[role] || [];
  return { ...matrix, [role]: cur.includes(perm) ? cur.filter((p) => p !== perm) : [...cur, perm] };
}

export function matrixChanges(before, after) {
  return Object.keys(after).map((role) => {
    const b = new Set(before[role] || []), a = new Set(after[role] || []);
    return { role, added: [...a].filter((p) => !b.has(p)), removed: [...b].filter((p) => !a.has(p)) };
  }).filter((c) => c.added.length || c.removed.length);
}

export function nextPath(p) {
  return typeof p === "string" && p.startsWith("/") && !p.startsWith("//") && !p.startsWith("/login") ? p : "/";
}
