// Layered layout for the network topology: one column per layer (core, access, host, service), each column
// ordered by its parent in the column to the left so lines cross as little as possible. Pure: data in, boxes out.

export const LAYERS = ["Core", "Access", "Hosts", "Services"];
export const BOX = { w: 196, h: 52, gap: 12, col: 268, top: 34 };

const BAD = new Set(["down", "unreachable", "cut off"]);

export function tone(n) {
  if (BAD.has(n.status)) return "bad";
  if (n.status === "missing" || n.status === "not polled") return "neutral";
  if (n.kind === "host" && !n.known) return "action"; // an unknown device: someone has to look at it
  return "ok";
}

export function statusLabel(n) {
  if (n.kind === "host" && !n.known && n.status === "up") return "Unknown device";
  return { up: "Up", down: "Down", unreachable: "Not answering", "cut off": "Cut off", missing: "Missing",
           "not polled": "Seen via LLDP" }[n.status] || n.status;
}

export function layout(topo) {
  const nodes = topo?.nodes || [];
  const links = topo?.links || [];
  const nbrs = new Map();
  for (const l of links) {
    if (!nbrs.has(l.a)) nbrs.set(l.a, []);
    if (!nbrs.has(l.b)) nbrs.set(l.b, []);
    nbrs.get(l.a).push(l.b);
    nbrs.get(l.b).push(l.a);
  }
  const cols = [0, 1, 2, 3].map((layer) => nodes.filter((n) => n.layer === layer));
  const rank = new Map();
  cols[0].sort((a, b) => a.name.localeCompare(b.name)).forEach((n, i) => rank.set(n.id, i));
  for (let c = 1; c < 4; c++) {
    const parentRank = (n) => {
      const ps = (nbrs.get(n.id) || []).filter((p) => rank.has(p) && nodes.find((x) => x.id === p)?.layer === c - 1);
      if (n.attached && rank.has(`dev:${n.attached.split(":")[0]}`)) return rank.get(`dev:${n.attached.split(":")[0]}`);
      return ps.length ? Math.min(...ps.map((p) => rank.get(p))) : 999;
    };
    cols[c].sort((a, b) => parentRank(a) - parentRank(b) || a.name.localeCompare(b.name)).forEach((n, i) => rank.set(n.id, i));
  }
  const tallest = Math.max(1, ...cols.map((c) => c.length));
  const height = BOX.top + tallest * (BOX.h + BOX.gap) + 8;
  const pos = new Map();
  cols.forEach((col, c) => {
    const offset = BOX.top + ((tallest - col.length) * (BOX.h + BOX.gap)) / 2;
    col.forEach((n, i) => pos.set(n.id, { x: c * BOX.col, y: offset + i * (BOX.h + BOX.gap) }));
  });
  const boxes = nodes.filter((n) => pos.has(n.id)).map((n) => ({ ...n, ...pos.get(n.id), tone: tone(n) }));
  const lines = links.filter((l) => pos.has(l.a) && pos.has(l.b)).map((l) => {
    let [p, q] = [pos.get(l.a), pos.get(l.b)];
    if (p.x > q.x) [p, q] = [q, p];
    const same = p.x === q.x;            // two core devices cabled together: draw on the left of the column
    const x1 = same ? p.x : p.x + BOX.w, y1 = p.y + BOX.h / 2;
    const x2 = q.x, y2 = q.y + BOX.h / 2;
    const d = same ? `M${x1},${y1} C${x1 - 40},${y1} ${x2 - 40},${y2} ${x2},${y2}`
      : `M${x1},${y1} C${x1 + 36},${y1} ${x2 - 36},${y2} ${x2},${y2}`;
    return { ...l, d };
  });
  return { boxes, lines, width: 3 * BOX.col + BOX.w + 2, height };
}
