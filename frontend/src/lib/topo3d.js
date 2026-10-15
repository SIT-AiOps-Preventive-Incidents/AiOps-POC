// Places the 3D topology like a network drawing, not a random cloud: the internet on top, gateways under it, one hub
// per network, the machines spread in a filled disc around their hub (a sunflower pattern, so hundreds of machines
// stay evenly spaced and readable instead of one giant ring), and the services in a small disc under their machine.
// The same graph always gets the same picture.

const Y = { internet: 170, gateway: 105, hub: 45, machine: 0, service: -36 };
const GOLDEN = Math.PI * (3 - Math.sqrt(5));   // the golden angle - what sunflowers use to pack points evenly
const STEP = 26;        // spacing between neighbouring machines
const STEP_S = 13;      // spacing between services under one machine

function ring(n, r, i, offset = 0) {
  if (n <= 1 && r === 0) return [0, 0];
  const a = offset + (2 * Math.PI * i) / Math.max(n, 1);
  return [r * Math.cos(a), r * Math.sin(a)];
}
function sunflower(i, step) {         // the i-th point of a filled disc, evenly spaced
  const r = step * Math.sqrt(i + 0.5);
  const a = i * GOLDEN;
  return [r * Math.cos(a), r * Math.sin(a)];
}
const discRadius = (n, step = STEP) => (n <= 1 ? step : step * Math.sqrt(n - 0.5));

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
  const machinesOf = (h) => (kids[h] || []).filter((c) => kind[c] !== "service");
  const pos = {};
  pos.internet = { x: 0, y: Y.internet, z: 0 };

  const hubs = graph.nodes.filter((n) => n.kind === "hub").map((n) => n.id).sort();
  // put each hub far enough apart that the biggest machine disc does not reach the next hub
  const maxDisc = Math.max(0, ...hubs.map((h) => discRadius(machinesOf(h).length)));
  const R = hubs.length <= 1 ? 0 : Math.max(240, maxDisc + 170);
  hubs.forEach((h, i) => {
    const [x, z] = ring(hubs.length, R, i);
    pos[h] = { x, y: Y.hub, z };
    machinesOf(h).forEach((c, j) => {
      const [dx, dz] = hubs.length === 1 || machinesOf(h).length > 6 ? sunflower(j, STEP)
        : ring(machinesOf(h).length, Math.max(60, machinesOf(h).length * 16), j, Math.PI / 2);
      pos[c] = { x: x + dx, y: Y.machine, z: z + dz };
      const s = (kids[c] || []).filter((k) => kind[k] === "service");
      s.forEach((sv, k) => {
        if (pos[sv]) return;
        const [sx, sz] = s.length <= 1 ? [0, STEP_S] : sunflower(k, STEP_S);
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
