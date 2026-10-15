// Run with: npm test (node --test, no extra dependencies)
import assert from "node:assert/strict";
import { test } from "node:test";
import { layout } from "./topo3d.js";

const graph = {
  nodes: [
    { id: "internet", kind: "internet" }, { id: "gw:a", kind: "gateway" }, { id: "hub:a", kind: "hub" },
    { id: "hub:b", kind: "hub" }, { id: "host:x", kind: "connected" }, { id: "ip:1", kind: "virtual machine" },
    { id: "host:y", kind: "connected" }, { id: "svc:s1", kind: "service" }, { id: "svc:s2", kind: "service" },
  ],
  links: [
    { source: "gw:a", target: "internet" }, { source: "hub:a", target: "gw:a" }, { source: "hub:b", target: "internet" },
    { source: "host:x", target: "hub:a" }, { source: "ip:1", target: "hub:a" }, { source: "host:y", target: "hub:b" },
    { source: "svc:s1", target: "host:x" }, { source: "svc:s2", target: "host:x" }, { source: "svc:s1", target: "svc:s2" },
  ],
};
const dist = (a, b) => Math.hypot(a.x - b.x, a.y - b.y, a.z - b.z);

test("every object gets a place, the same place every time", () => {
  const p = layout(graph);
  assert.equal(Object.keys(p).length, graph.nodes.length);
  assert.deepEqual(layout(graph), p);
});

test("layers top to bottom: internet, gateways, hubs, machines, services", () => {
  const p = layout(graph);
  assert.ok(p.internet.y > p["gw:a"].y && p["gw:a"].y > p["hub:a"].y);
  assert.ok(p["hub:a"].y > p["host:x"].y && p["host:x"].y > p["svc:s1"].y);
});

test("machines sit around their own hub, services around their own machine", () => {
  const p = layout(graph);
  assert.ok(dist(p["host:x"], p["hub:a"]) < dist(p["host:x"], p["hub:b"]));
  assert.ok(dist(p["ip:1"], p["hub:a"]) < dist(p["ip:1"], p["hub:b"]));
  assert.ok(dist(p["svc:s1"], p["host:x"]) < dist(p["svc:s1"], p["host:y"]));
  assert.ok(dist(p["host:x"], p["ip:1"]) > 10);                                 // not on top of each other
});
