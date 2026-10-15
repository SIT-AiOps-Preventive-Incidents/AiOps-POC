<script setup>
// 3D topology: internet -> gateways -> one hub per network -> machines -> services. Drag to turn, scroll to zoom,
// click an object for its details, double-click to fly to it. Packets travel along the lines between services
// that talk to each other.
import { computed, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import { useRouter } from "vue-router";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { CSS2DObject, CSS2DRenderer } from "three/examples/jsm/renderers/CSS2DRenderer.js";
import { api } from "@/lib/api";
import { layout } from "@/lib/topo3d";

const router = useRouter();
const box = ref(null);
const graph = shallowRef(null);
const selected = ref(null);
const showServices = ref(true);
const spin = ref(!window.matchMedia("(prefers-reduced-motion: reduce)").matches);
const error = ref("");
const noGl = ref(false);

const KIND = { internet: "Internet", gateway: "Gateway", hub: "Network", connected: "Server on AIOps", "virtual machine": "Virtual machine",
  container: "Container", device: "Device", "random MAC": "Device (random MAC)", service: "Service" };
const counts = computed(() => {
  const c = {};
  for (const n of graph.value?.nodes || []) c[n.kind] = (c[n.kind] || 0) + 1;
  return c;
});

let renderer, labels, scene, camera, controls, raf, ro, objects = [], pickables = [], packets = [], hovered = null, flyTo = null;
const css = (name, fb) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb;

function colors() {
  return { primary: css("--c-primary", "#2563eb"), ok: css("--c-ok", "#16a34a"), bad: css("--c-bad", "#e5383b"),
    text: css("--c-text", "#111827"), muted: css("--c-text-3", "#9aa3b2"), line: css("--c-separator", "#d5dae3"),
    hub: "#f59e0b", navy: "#0d1b4c" };
}
const statusColor = (s, c) => (["problem", "down", "error"].includes(s) ? c.bad : ["healthy", "ok", "online"].includes(s) ? c.ok : c.muted);

function mesh(n, c) {
  const g = new THREE.Group();
  const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.55, metalness: 0.1, ...extra });
  if (n.kind === "internet") {
    g.add(new THREE.Mesh(new THREE.IcosahedronGeometry(15, 1), mat(c.primary, { wireframe: true })));
    g.add(new THREE.Mesh(new THREE.SphereGeometry(12, 24, 16), mat(c.primary, { transparent: true, opacity: 0.18 })));
  } else if (n.kind === "gateway") {
    g.add(new THREE.Mesh(new THREE.CylinderGeometry(12, 12, 6, 32), mat(c.navy)));
    for (const dx of [-6, 6]) {
      const a = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 9), mat(c.navy));
      a.position.set(dx, 7, 0); g.add(a);
    }
  } else if (n.kind === "hub") {
    g.add(new THREE.Mesh(new THREE.BoxGeometry(48, 6, 14), mat(c.hub, n.estimated ? { transparent: true, opacity: 0.55 } : {})));
    for (let i = 0; i < 10; i++) {
      const port = new THREE.Mesh(new THREE.BoxGeometry(2.4, 2, 0.6), mat("#3b2a07"));
      port.position.set(-19 + i * 4.2, 0, 7.1); g.add(port);
    }
  } else if (n.kind === "service") {
    g.add(new THREE.Mesh(new THREE.SphereGeometry(3.4, 20, 14), mat(statusColor(n.status, c), { emissive: statusColor(n.status, c), emissiveIntensity: 0.25 })));
  } else {
    const on = n.kind === "connected";
    const s = on ? 1 : 0.72;
    const screen = new THREE.Mesh(new THREE.BoxGeometry(18 * s, 12 * s, 1.6), mat(on ? c.navy : "#5d6578"));
    screen.position.y = 9 * s; g.add(screen);
    const stripe = new THREE.Mesh(new THREE.BoxGeometry(18 * s, 1.6 * s, 1.7), mat(on ? statusColor(n.status, c) : c.hub));
    stripe.position.y = 3.6 * s; g.add(stripe);
    const stand = new THREE.Mesh(new THREE.BoxGeometry(3 * s, 3 * s, 1.2), mat("#2a3245"));
    stand.position.y = 1.5 * s; g.add(stand);
    if (on) { const kb = new THREE.Mesh(new THREE.BoxGeometry(14, 1, 5), mat("#2a3245")); kb.position.set(0, 0.5, 5); g.add(kb); }
  }
  g.userData.node = n;
  return g;
}

function label(text, cls) {
  const el = document.createElement("div");
  el.className = `t3-label ${cls || ""}`;
  el.textContent = text;
  return new CSS2DObject(el);
}

function build() {
  for (const o of objects) scene.remove(o);
  objects = []; pickables = []; packets = [];
  const g = graph.value;
  if (!g) return;
  const c = colors();
  const pos = layout(g);
  const shown = (n) => showServices.value || n.kind !== "service";
  const add = (o) => { scene.add(o); objects.push(o); };
  for (const n of g.nodes) {
    if (!shown(n)) continue;
    const o = mesh(n, c);
    const p = pos[n.id];
    o.position.set(p.x, p.y, p.z);
    if (n.kind !== "service" || g.nodes.length < 40) {
      const l = label(n.label, n.kind);
      l.position.set(0, n.kind === "service" ? 6 : n.kind === "hub" ? 9 : n.kind === "internet" ? 21 : 22 * (n.kind === "connected" ? 1 : 0.72), 0);
      o.add(l);
    }
    add(o); pickables.push(o);
  }
  for (const l of g.links) {
    const a = g.nodes.find((n) => n.id === l.source), b = g.nodes.find((n) => n.id === l.target);
    if (!a || !b || !shown(a) || !shown(b)) continue;
    const pa = pos[l.source], pb = pos[l.target];
    const pts = [new THREE.Vector3(pa.x, pa.y, pa.z), new THREE.Vector3(pb.x, pb.y, pb.z)];
    const talks = l.kind === "talks";
    const heard = a.status === "heard";
    const mat = talks ? new THREE.LineBasicMaterial({ color: c.primary, transparent: true, opacity: 0.85 })
      : new THREE.LineDashedMaterial({ color: heard ? c.muted : "#7b8496", dashSize: heard ? 2 : 4, gapSize: heard ? 3 : 1.5 });
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat);
    if (!talks) line.computeLineDistances();
    add(line);
    if (talks) {
      const dot = new THREE.Mesh(new THREE.SphereGeometry(1.3, 10, 8), new THREE.MeshBasicMaterial({ color: c.primary }));
      add(dot);
      packets.push({ dot, from: pts[0], to: pts[1], t: Math.random() });
    }
  }
}

function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  const m = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  const ray = new THREE.Raycaster();
  ray.setFromCamera(m, camera);
  const hit = ray.intersectObjects(pickables, true)[0];
  let o = hit?.object;
  while (o && !o.userData.node) o = o.parent;
  return o || null;
}
function onMove(ev) {
  const o = pick(ev);
  if (hovered && hovered !== o) hovered.scale.setScalar(1);
  hovered = o;
  if (o) o.scale.setScalar(1.18);
  renderer.domElement.style.cursor = o ? "pointer" : "grab";
}
function onClick(ev) { const o = pick(ev); selected.value = o ? o.userData.node : null; }
function onDouble(ev) {
  const o = pick(ev);
  if (!o) return;
  const p = o.position.clone();
  flyTo = { target: p, cam: p.clone().add(new THREE.Vector3(0, 40, 90)) };
}
let home = { target: new THREE.Vector3(0, 40, 0), cam: new THREE.Vector3(0, 230, 420) };
function frame() {   // camera that fits everything: centre of all objects, far enough for the widest ring
  const b = new THREE.Box3();
  for (const o of pickables) b.expandByPoint(o.position);
  if (b.isEmpty()) return;
  const c = b.getCenter(new THREE.Vector3());
  const r = Math.max(b.getSize(new THREE.Vector3()).length() / 2, 120);
  home = { target: c, cam: c.clone().add(new THREE.Vector3(0, r * 0.75, r * 1.9)) };
}
function resetView() { flyTo = { ...home }; }

function loop() {
  raf = requestAnimationFrame(loop);
  for (const p of packets) {
    p.t = (p.t + 0.006) % 1;
    p.dot.position.lerpVectors(p.from, p.to, p.t);
  }
  if (flyTo) {
    controls.target.lerp(flyTo.target, 0.08);
    camera.position.lerp(flyTo.cam, 0.08);
    if (camera.position.distanceTo(flyTo.cam) < 1) flyTo = null;
  }
  controls.autoRotate = spin.value && !flyTo && !selected.value;
  controls.update();
  renderer.render(scene, camera);
  labels.render(scene, camera);
}

function size() {
  const w = box.value.clientWidth, h = box.value.clientHeight;
  renderer.setSize(w, h); labels.setSize(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}

let framed = false;
async function load() {
  try {
    graph.value = await api.network.graph(); error.value = ""; build(); frame();
    if (!framed) { framed = true; camera.position.copy(home.cam); controls.target.copy(home.target); }
  } catch (e) { error.value = e.message; }
}

let timer;
onMounted(async () => {
  const probe = document.createElement("canvas");
  if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) {   // still list what is there, just not in 3D
    noGl.value = true;
    try { graph.value = await api.network.graph(); } catch (e) { error.value = e.message; }
    return;
  }
  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(45, 1, 1, 5000);
  camera.position.set(0, 230, 420);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  box.value.appendChild(renderer.domElement);
  labels = new CSS2DRenderer();
  labels.domElement.className = "t3-labels";
  box.value.appendChild(labels.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.autoRotateSpeed = 0.6; controls.target.set(0, 40, 0);
  controls.addEventListener("start", () => { flyTo = null; });
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8899aa, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.4); sun.position.set(120, 300, 200); scene.add(sun);
  const floor = new THREE.GridHelper(900, 36, 0xc9cfdb, 0xe4e8ef); floor.position.y = -46; floor.material.transparent = true; floor.material.opacity = 0.5;
  scene.add(floor);
  renderer.domElement.addEventListener("pointermove", onMove);
  renderer.domElement.addEventListener("click", onClick);
  renderer.domElement.addEventListener("dblclick", onDouble);
  ro = new ResizeObserver(size); ro.observe(box.value); size();
  await load();
  timer = setInterval(load, 30000);
  loop();
});
onBeforeUnmount(() => {
  cancelAnimationFrame(raf); clearInterval(timer); ro?.disconnect(); controls?.dispose(); renderer?.dispose();
});
const toggleServices = () => { showServices.value = !showServices.value; build(); };
const open = () => selected.value?.link && router.push(selected.value.link);
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader title="Network in 3D" subtitle="Internet, gateways, one hub per network, the machines on it and the services they run. Drag to turn, scroll to zoom, click for details, double-click to fly in.">
      <UiButton variant="tint" icon="list" to="/network/yours">List</UiButton>
      <UiButton variant="tint" icon="flowchart" to="/network">Research lab (NIKA)</UiButton>
    </UiPageHeader>
    <div class="bar">
      <div class="row"><UiSwitch :model-value="showServices" label="Show services" @update:model-value="toggleServices" /><span>Services</span></div>
      <div class="row"><UiSwitch v-model="spin" label="Turn slowly" /><span>Turn slowly</span></div>
      <UiButton variant="plain" size="sm" icon="arrow_sync" @click="resetView">Reset view</UiButton>
      <span class="legend">
        <span v-for="(n, k) in counts" :key="k"><i :class="`k-${k.replace(/\s/g, '-')}`" />{{ n }} {{ KIND[k] || k }}</span>
      </span>
    </div>
    <p v-if="error" class="bad small">{{ error }}</p>
    <div class="stage">
      <div ref="box" class="canvas" />
      <div v-if="noGl" class="nogl"><b>This browser cannot draw 3D</b><span class="muted small">WebGL is turned off or not supported. The same machines are listed on the List page.</span>
        <UiButton size="sm" to="/network/yours">Open the list</UiButton></div>
      <aside v-if="selected" class="panel">
        <div class="ptitle"><b>{{ selected.label }}</b><UiButton variant="plain" size="sm" icon="dismiss" aria-label="Close" @click="selected = null" /></div>
        <div class="muted small">{{ KIND[selected.kind] || selected.kind }}<template v-if="selected.estimated"> · estimated from an IP address</template></div>
        <dl>
          <template v-if="selected.ip"><dt>IP</dt><dd>{{ selected.ip }}</dd></template>
          <template v-if="selected.mac"><dt>MAC</dt><dd>{{ selected.mac }}</dd></template>
          <template v-if="selected.vendor"><dt>Made by</dt><dd>{{ selected.vendor }}</dd></template>
          <template v-if="selected.owner"><dt>Owner</dt><dd>{{ selected.owner }}</dd></template>
          <template v-if="selected.status"><dt>Status</dt><dd>{{ selected.status === "heard" ? "heard on the network, not on AIOps" : selected.status }}</dd></template>
        </dl>
        <UiButton v-if="selected.link" size="sm" @click="open">Open</UiButton>
      </aside>
    </div>
  </div>
</template>
<style scoped>
.bar { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; margin-bottom: 12px; }
.legend { display: flex; gap: 14px; flex-wrap: wrap; margin-left: auto; font-size: var(--fs-sm); color: var(--c-text-2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 10px; height: 10px; border-radius: 3px; background: var(--c-text-3); }
.legend .k-hub { background: #f59e0b; } .legend .k-gateway { background: #0d1b4c; } .legend .k-connected { background: var(--c-ok); }
.legend .k-service { background: var(--c-primary); border-radius: 50%; } .legend .k-internet { background: var(--c-primary); }
.stage { position: relative; height: calc(100vh - 230px); min-height: 460px; border-radius: var(--radius-lg); background: var(--c-surface);
  box-shadow: var(--shadow-1); overflow: hidden; }
.canvas { position: absolute; inset: 0; }
.canvas :deep(canvas) { display: block; cursor: grab; }
.canvas :deep(.t3-labels) { position: absolute; top: 0; left: 0; pointer-events: none; }
.canvas :deep(.t3-label) { font: 600 12px/1.2 var(--font, inherit); color: var(--c-text); background: var(--c-surface); padding: 2px 6px;
  border-radius: 6px; box-shadow: var(--shadow-1); white-space: nowrap; }
.canvas :deep(.t3-label.service) { font-weight: 500; font-size: 11px; color: var(--c-text-2); }
.canvas :deep(.t3-label.hub) { background: #f59e0b; color: #1b1300; }
.nogl { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 8px; text-align: center; }
.panel { position: absolute; top: 14px; right: 14px; width: 280px; background: var(--c-surface); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-2, var(--shadow-1)); padding: 14px 16px; }
.ptitle { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ptitle b { font-size: var(--fs-lg); overflow-wrap: anywhere; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 12px 0; font-size: var(--fs-sm); }
dt { color: var(--c-text-3); } dd { margin: 0; overflow-wrap: anywhere; }
@media (max-width: 760px) { .panel { left: 10px; right: 10px; width: auto; top: auto; bottom: 10px; } .legend { margin-left: 0; } }
</style>
