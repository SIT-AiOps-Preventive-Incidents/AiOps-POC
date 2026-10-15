// Places the 3D topology like a network drawing, not a random cloud: the internet on top, gateways under it, one hub
// per network, the machines in a ring around their hub, and the services in a small ring under their machine.
// The same graph always gets the same picture.

const Y = { internet: 170, gateway: 105, hub: 45, machine: 0, service: -36 };

function ring(n, r, i, offset = 0) {
  if (n <= 1 && r === 0) return [0, 0];
  const a = offset + (2 * Math.PI * i) / Math.max(n, 1);
  return [r * Math.cos(a), r * Math.sin(a)];
}

export function layout(graph) {
  const kind = Object.fromEntries(graph.nodes.map((n) => [n.id, n.kind]));
  const up = {};   // child -> parent (first one wins: a service on two machines sits under the first)
  for (const l of graph.links) {
    if (l.kind === "talks" || up[l.source]) continue;
    up[l.source] = l.target;
  }
  const kids = {};
  for (const [c, p] of Object.entries(up)) (kids[p] ||= []).push(c);
  for (const k of Object.values(kids)) k.sort();
  const pos = {};
  pos.internet = { x: 0, y: Y.internet, z: 0 };

  const hubs = graph.nodes.filter((n) => n.kind === "hub").map((n) => n.id).sort();
  const R = hubs.length <= 1 ? 0 : Math.max(150, hubs.length * 75);
  hubs.forEach((h, i) => {
    const [x, z] = ring(hubs.length, R, i);
    pos[h] = { x, y: Y.hub, z };
    const m = (kids[h] || []).filter((c) => kind[c] !== "service");
    const r = Math.max(60, m.length * 16);
    m.forEach((c, j) => {
      const [dx, dz] = ring(m.length, r, j, Math.PI / 2);
      pos[c] = { x: x + dx, y: Y.machine, z: z + dz };
      const s = (kids[c] || []).filter((k) => kind[k] === "service");
      const rs = Math.max(18, s.length * 5);
      s.forEach((sv, k) => {
        if (pos[sv]) return;
        const [sx, sz] = ring(s.length, rs, k);
        pos[sv] = { x: x + dx + sx, y: Y.service, z: z + dz + sz };
      });
    });
  });
  // gateways float above the hubs they serve
  for (const n of graph.nodes.filter((n) => n.kind === "gateway")) {
    const below = (kids[n.id] || []).map((h) => pos[h]).filter(Boolean);
    const x = below.length ? below.reduce((a, p) => a + p.x, 0) / below.length : 0;
    const z = below.length ? below.reduce((a, p) => a + p.z, 0) / below.length : 0;
    pos[n.id] = { x, y: Y.gateway, z };
  }
  // anything left (a service whose machine is unknown) waits at the side instead of piling up at the centre
  let spare = 0;
  for (const n of graph.nodes) if (!pos[n.id]) pos[n.id] = { x: -60 - 20 * spare++, y: Y.service, z: -60 };
  return pos;
}
