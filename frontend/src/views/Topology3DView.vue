<script setup>
// 3D topology: internet -> gateways -> one hub per network -> machines -> services. Drag to turn, scroll to zoom,
// click an object for its details, double-click to fly to it. Packets travel along the lines between services
// that talk to each other.
import { computed, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import { usePageFacts } from "@/composables/usePageFacts";
import { useRouter } from "vue-router";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import { Line2 } from "three/examples/jsm/lines/Line2.js";
import { LineGeometry } from "three/examples/jsm/lines/LineGeometry.js";
import { LineMaterial } from "three/examples/jsm/lines/LineMaterial.js";
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

const KIND = { internet: "Internet", gateway: "Gateway", hub: "Network", connected: "Server on SIT-AIOPS", "virtual machine": "Virtual machine",
  container: "Container", device: "Device", "random MAC": "Device (random MAC)", service: "Service" };
const counts = computed(() => {
  const c = {};
  for (const n of graph.value?.nodes || []) c[n.kind] = (c[n.kind] || 0) + 1;
  return c;
});

let renderer, labels, scene, camera, controls, raf, ro, hoverLabel, selectionRing;
let objects = [], pickables = [], packets = [], lineMaterials = [], hovered = null, flyTo = null;
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const css = (name, fb) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fb;

function colors() {
  return {
    primary: css("--c-primary", "#2fc98b"), ok: css("--c-ok", "#2fcf8e"), bad: css("--c-bad", "#f2545b"),
    text: css("--c-text", "#f4f4f5"), muted: css("--c-text-3", "#6f727b"), line: css("--c-separator", "#1f2125"),
    bg: css("--c-surface", "#141417"), fill: css("--c-fill", "#1c1d21"), border: css("--c-border", "#24262b"),
    gauge: css("--c-gauge", "#56b6ea"), viz: css("--c-viz", "#9474f2"),
  };
}
const statusColor = (s, c) => (["problem", "down", "error"].includes(s) ? c.bad : ["healthy", "ok", "online"].includes(s) ? c.ok : c.muted);

function mesh(n, c) {
  const g = new THREE.Group();
  const mat = (color, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.46, metalness: 0.16, ...extra });
  const glow = (color, opacity = 0.18) => new THREE.MeshBasicMaterial({
    color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false,
  });
  if (n.kind === "internet") {
    g.add(new THREE.Mesh(new THREE.IcosahedronGeometry(16, 2), mat(c.primary, { wireframe: true, emissive: c.primary, emissiveIntensity: 0.38 })));
    g.add(new THREE.Mesh(new THREE.SphereGeometry(12, 24, 16), glow(c.primary, 0.14)));
    const orbit = new THREE.Mesh(new THREE.TorusGeometry(23, 0.45, 8, 64), glow(c.gauge, 0.62));
    orbit.rotation.x = Math.PI / 2.7; orbit.rotation.z = Math.PI / 7; g.add(orbit);
  } else if (n.kind === "gateway") {
    g.add(new THREE.Mesh(new THREE.CylinderGeometry(12, 12, 6, 32), mat(c.gauge, { emissive: c.gauge, emissiveIntensity: 0.08 })));
    const rim = new THREE.Mesh(new THREE.TorusGeometry(12.3, 0.6, 8, 48), glow(c.gauge, 0.55));
    rim.rotation.x = Math.PI / 2; rim.position.y = 2.7; g.add(rim);
    for (const dx of [-6, 6]) {
      const a = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 9), mat(c.gauge));
      a.position.set(dx, 7, 0); g.add(a);
    }
  } else if (n.kind === "hub") {
    g.add(new THREE.Mesh(new RoundedBoxGeometry(48, 6, 14, 4, 1.4), mat(c.viz, n.estimated ? { transparent: true, opacity: 0.55 } : {})));
    for (let i = 0; i < 10; i++) {
      const port = new THREE.Mesh(new THREE.BoxGeometry(2.4, 2, 0.6), mat(i % 3 === 0 ? c.primary : c.fill, { emissive: i % 3 === 0 ? c.primary : c.fill, emissiveIntensity: 0.35 }));
      port.position.set(-19 + i * 4.2, 0, 7.1); g.add(port);
    }
  } else if (n.kind === "service") {
    const tone = statusColor(n.status, c);
    g.add(new THREE.Mesh(new THREE.SphereGeometry(3.6, 20, 14), mat(tone, { emissive: tone, emissiveIntensity: 0.48 })));
    g.add(new THREE.Mesh(new THREE.SphereGeometry(5.4, 16, 12), glow(tone, 0.1)));
  } else {
    const on = n.kind === "connected";
    const s = on ? 1 : 0.72;
    const screen = new THREE.Mesh(new RoundedBoxGeometry(18 * s, 12 * s, 1.6, 3, 0.55), mat(on ? c.gauge : c.muted));
    screen.position.y = 9 * s; g.add(screen);
    const stripeTone = on ? statusColor(n.status, c) : c.viz;
    const stripe = new THREE.Mesh(new RoundedBoxGeometry(18 * s, 1.6 * s, 1.7, 2, 0.35), mat(stripeTone, { emissive: stripeTone, emissiveIntensity: 0.22 }));
    stripe.position.y = 3.6 * s; g.add(stripe);
    const stand = new THREE.Mesh(new THREE.BoxGeometry(3 * s, 3 * s, 1.2), mat(c.fill));
    stand.position.y = 1.5 * s; g.add(stand);
    if (on) { const kb = new THREE.Mesh(new RoundedBoxGeometry(14, 1, 5, 2, 0.35), mat(c.fill)); kb.position.set(0, 0.5, 5); g.add(kb); }
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

function disposeObject(root) {
  root.traverse((o) => {
    if (o.isCSS2DObject) o.element?.remove();
    o.geometry?.dispose?.();
    const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
    for (const m of mats) m.dispose?.();
  });
  scene.remove(root);
}
function clearObjects() {
  for (const o of objects) disposeObject(o);
  objects = []; pickables = []; packets = []; lineMaterials = []; hovered = null;
  if (hoverLabel) hoverLabel.visible = false;
}
function curveBetween(a, b, talks) {
  const mid = a.clone().lerp(b, 0.5);
  const distance = a.distanceTo(b);
  mid.y += talks ? Math.max(12, distance * 0.12) : Math.min(18, distance * 0.055);
  return new THREE.QuadraticBezierCurve3(a, mid, b);
}

function build() {
  clearObjects();
  const g = graph.value;
  if (!g) return;
  const c = colors();
  const pos = layout(g);
  const shown = (n) => showServices.value || n.kind !== "service";
  const add = (o) => { scene.add(o); objects.push(o); };
  const byId = Object.fromEntries(g.nodes.map((n) => [n.id, n]));

  // A quiet footprint under each network keeps dense machine groups readable without turning the view into a chart.
  for (const hub of g.nodes.filter((n) => n.kind === "hub")) {
    const centre = pos[hub.id];
    if (!centre) continue;
    const neighbours = g.links
      .map((l) => l.source === hub.id ? l.target : l.target === hub.id ? l.source : null)
      .filter((id) => id && byId[id] && !["internet", "gateway", "hub", "service"].includes(byId[id].kind))
      .map((id) => pos[id]).filter(Boolean);
    const radius = Math.max(42, ...neighbours.map((p) => Math.hypot(p.x - centre.x, p.z - centre.z) + 22));
    const footprint = new THREE.Mesh(
      new THREE.CircleGeometry(radius, 64),
      new THREE.MeshBasicMaterial({ color: c.viz, transparent: true, opacity: 0.025, side: THREE.DoubleSide, depthWrite: false }),
    );
    footprint.rotation.x = -Math.PI / 2; footprint.position.set(centre.x, -45.5, centre.z); add(footprint);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(radius - 0.7, radius, 64),
      new THREE.MeshBasicMaterial({ color: c.viz, transparent: true, opacity: 0.25, side: THREE.DoubleSide, depthWrite: false }),
    );
    ring.rotation.x = -Math.PI / 2; ring.position.set(centre.x, -45, centre.z); add(ring);
  }

  // With many machines, a label on every one is a wall of text. Keep labels on the structural nodes
  // (internet, gateways, hubs, our own servers) and show a discovered machine's name on hover instead.
  const dense = g.nodes.length > 30;
  const structural = (k) => ["internet", "gateway", "hub", "connected"].includes(k);
  for (const n of g.nodes) {
    if (!shown(n)) continue;
    const o = mesh(n, c);
    const p = pos[n.id];
    o.position.set(p.x, p.y, p.z);
    const labelled = structural(n.kind) || (!dense && (n.kind !== "service" || g.nodes.length < 40));
    if (labelled) {
      const l = label(n.label, n.kind);
      l.position.set(0, n.kind === "service" ? 6 : n.kind === "hub" ? 9 : n.kind === "internet" ? 21 : 22 * (n.kind === "connected" ? 1 : 0.72), 0);
      o.add(l);
    }
    add(o); pickables.push(o);
  }
  for (const l of g.links) {
    const a = byId[l.source], b = byId[l.target];
    if (!a || !b || !shown(a) || !shown(b)) continue;
    const pa = pos[l.source], pb = pos[l.target];
    const talks = l.kind === "talks";
    const heard = a.status === "heard";
    const from = new THREE.Vector3(pa.x, pa.y, pa.z), to = new THREE.Vector3(pb.x, pb.y, pb.z);
    const curve = curveBetween(from, to, talks);
    const pts = curve.getPoints(talks ? 32 : 20);
    const geometry = new LineGeometry();
    geometry.setPositions(pts.flatMap((p) => [p.x, p.y, p.z]));
    const mat = new LineMaterial({
      color: talks ? c.primary : heard ? c.muted : c.gauge,
      linewidth: talks ? 2.25 : 1.1,
      transparent: true,
      opacity: talks ? 0.78 : heard ? 0.3 : 0.42,
      dashed: !talks,
      dashScale: 1,
      dashSize: heard ? 2 : 4,
      gapSize: heard ? 3 : 2,
      depthWrite: false,
    });
    mat.resolution.set(box.value.clientWidth, box.value.clientHeight);
    lineMaterials.push(mat);
    const line = new Line2(geometry, mat);
    if (!talks) line.computeLineDistances();
    add(line);
    if (talks) {
      const dot = new THREE.Mesh(
        new THREE.SphereGeometry(1.45, 10, 8),
        new THREE.MeshBasicMaterial({ color: c.primary, transparent: true, opacity: 0.92, blending: THREE.AdditiveBlending, depthWrite: false }),
      );
      add(dot);
      packets.push({ dot, curve, t: Math.random() });
    }
  }
  if (selected.value) {
    const o = pickables.find((p) => p.userData.node.id === selected.value.id);
    if (o) showSelection(o);
  }
}

function pick(ev) {
  const r = renderer.domElement.getBoundingClientRect();
  pointer.set(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
  raycaster.setFromCamera(pointer, camera);
  const hit = raycaster.intersectObjects(pickables, true)[0];
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
  if (hoverLabel) {   // name-on-hover, so a crowded segment stays readable without a label on every node
    const n = o?.userData.node;
    if (n) {
      hoverLabel.element.textContent = n.ip && n.ip !== n.label ? `${n.label} · ${n.ip}` : n.label;
      hoverLabel.position.copy(o.position).add(new THREE.Vector3(0, 16, 0));
      hoverLabel.visible = true;
    } else {
      hoverLabel.visible = false;
    }
  }
}
function showSelection(o) {
  if (!selectionRing || !o) return;
  const n = o.userData.node;
  const [radius, offset] = {
    internet: [27, -17], gateway: [17, -4], hub: [31, -5], service: [8, -3], connected: [17, -1],
  }[n.kind] || [13, -1];
  selectionRing.position.copy(o.position);
  selectionRing.position.y += offset;
  selectionRing.scale.setScalar(radius / 11);
  selectionRing.visible = true;
}
function selectObject(o) {
  selected.value = o ? o.userData.node : null;
  if (o) showSelection(o);
  else if (selectionRing) selectionRing.visible = false;
}
function clearSelection() { selectObject(null); }
function onClick(ev) { selectObject(pick(ev)); }
function onDouble(ev) {
  const o = pick(ev);
  if (!o) return;
  selectObject(o);
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
  if (!renderer || document.hidden) return;
  for (const p of packets) {
    p.t = (p.t + 0.006) % 1;
    p.dot.position.copy(p.curve.getPoint(p.t));
  }
  if (flyTo) {
    controls.target.lerp(flyTo.target, 0.08);
    camera.position.lerp(flyTo.cam, 0.08);
    if (camera.position.distanceTo(flyTo.cam) < 1) flyTo = null;
  }
  if (selectionRing?.visible) {
    const t = performance.now() * 0.001;
    selectionRing.rotation.z = t * 0.45;
    selectionRing.material.opacity = 0.58 + Math.sin(t * 2.4) * 0.15;
  }
  controls.autoRotate = spin.value && !flyTo && !selected.value;
  controls.update();
  renderer.render(scene, camera);
  labels.render(scene, camera);
}

function size() {
  const w = box.value.clientWidth, h = box.value.clientHeight;
  renderer.setSize(w, h); labels.setSize(w, h);
  for (const m of lineMaterials) m.resolution.set(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}

const query = ref("");
function goTo() {
  const q = query.value.trim().toLowerCase();
  if (!q) return;
  const o = pickables.find((o) => {
    const n = o.userData.node;
    return (n.label || "").toLowerCase().includes(q) || (n.ip || "").includes(q);
  });
  if (!o) { error.value = `No machine matches "${query.value}"`; return; }
  error.value = "";
  selectObject(o);
  if (hovered) hovered.scale.setScalar(1);
  o.scale.setScalar(1.12); hovered = o;
  const p = o.position.clone();
  flyTo = { target: p, cam: p.clone().add(new THREE.Vector3(0, 28, 66)) };
}

watch(selected, (n) => { if (!n && selectionRing) selectionRing.visible = false; });

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
  const c = colors();
  scene.fog = new THREE.FogExp2(c.bg, 0.00125);
  camera = new THREE.PerspectiveCamera(45, 1, 1, 5000);
  camera.position.set(0, 230, 420);
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.08;
  renderer.setClearColor(0x000000, 0);
  box.value.appendChild(renderer.domElement);
  labels = new CSS2DRenderer();
  labels.domElement.className = "t3-labels";
  box.value.appendChild(labels.domElement);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.065;
  controls.autoRotateSpeed = 0.5;
  controls.minDistance = 48;
  controls.maxDistance = 1800;
  controls.maxPolarAngle = Math.PI * 0.9;
  controls.screenSpacePanning = true;
  controls.target.set(0, 40, 0);
  controls.addEventListener("start", () => { flyTo = null; });
  scene.add(new THREE.HemisphereLight(0xffffff, new THREE.Color(c.bg), 1.35));
  const sun = new THREE.DirectionalLight(0xffffff, 1.8); sun.position.set(120, 300, 200); scene.add(sun);
  const rim = new THREE.PointLight(new THREE.Color(c.viz), 24, 620, 2); rim.position.set(-220, 110, -160); scene.add(rim);
  const accent = new THREE.PointLight(new THREE.Color(c.gauge), 18, 520, 2); accent.position.set(240, 40, 180); scene.add(accent);
  const floor = new THREE.GridHelper(900, 42, new THREE.Color(c.border), new THREE.Color(c.line));
  floor.position.y = -46; floor.material.transparent = true; floor.material.opacity = 0.22;
  scene.add(floor);
  selectionRing = new THREE.Mesh(
    new THREE.RingGeometry(9.4, 11, 64),
    new THREE.MeshBasicMaterial({
      color: c.primary, transparent: true, opacity: 0.7, side: THREE.DoubleSide,
      blending: THREE.AdditiveBlending, depthWrite: false,
    }),
  );
  selectionRing.rotation.x = -Math.PI / 2;
  selectionRing.visible = false;
  scene.add(selectionRing);
  const hl = document.createElement("div"); hl.className = "t3-label t3-hover";
  hoverLabel = new CSS2DObject(hl); hoverLabel.visible = false; scene.add(hoverLabel);
  renderer.domElement.addEventListener("pointermove", onMove);
  renderer.domElement.addEventListener("click", onClick);
  renderer.domElement.addEventListener("dblclick", onDouble);
  ro = new ResizeObserver(size); ro.observe(box.value); size();
  await load();
  timer = setInterval(load, 30000);
  loop();
});
onBeforeUnmount(() => {
  cancelAnimationFrame(raf); clearInterval(timer); ro?.disconnect(); controls?.dispose();
  clearObjects();
  scene?.traverse((o) => {
    o.geometry?.dispose?.();
    const mats = Array.isArray(o.material) ? o.material : o.material ? [o.material] : [];
    for (const m of mats) m.dispose?.();
  });
  hoverLabel?.element?.remove();
  renderer?.dispose();
});
const toggleServices = () => { showServices.value = !showServices.value; build(); };
const open = () => selected.value?.link && router.push(selected.value.link);
usePageFacts(() => graph.value ? {
  known_machines: graph.value.nodes.filter((n) => n.id.startsWith("host:") || n.id.startsWith("ip:") || n.kind === "cloud instance").length,
  networks: counts.value.hub ?? 0,
  ...(error.value ? { stale_data: 1 } : {}),
} : {});
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Fleet" title="Fleet in 3D" subtitle="Internet, gateways, one hub per network, and the machines on it. Drag to turn, scroll to zoom, click for details, double-click to fly in.">
      <UiButton variant="tint" icon="flowchart" to="/network">Map</UiButton>
      <UiButton variant="tint" icon="list" to="/network/list">List</UiButton>
    </UiPageHeader>
    <div class="bar">
      <div class="search"><UiField v-model="query" placeholder="Find a machine by name or IP" @enter="goTo" /><UiButton size="sm" icon="search" @click="goTo">Find</UiButton></div>
      <div class="row"><UiSwitch :model-value="showServices" label="Show services" @update:model-value="toggleServices" /><span>Services</span></div>
      <div class="row"><UiSwitch v-model="spin" label="Turn slowly" /><span>Turn slowly</span></div>
      <UiButton variant="plain" size="sm" icon="arrow_sync" @click="resetView">Reset view</UiButton>
      <span class="legend">
        <span v-for="(n, k) in counts" :key="k"><i :class="`k-${k.replace(/\s/g, '-')}`" />{{ n }} {{ KIND[k] || k }}</span>
      </span>
    </div>
    <p v-if="error" class="bad small">{{ error }}</p>
    <div class="stage" role="region" aria-label="Interactive 3D fleet topology. Use the Map or List view for a non-3D representation.">
      <div ref="box" class="canvas" />
      <div v-if="noGl" class="nogl"><b>This browser cannot draw 3D</b><span class="muted small">WebGL is turned off or not supported. The same machines are listed on the List page.</span>
        <UiButton size="sm" to="/network/list">Open the list</UiButton></div>
      <aside v-if="selected" class="panel">
        <div class="ptitle"><b>{{ selected.label }}</b><UiButton variant="plain" size="sm" icon="dismiss" aria-label="Close" @click="clearSelection" /></div>
        <div class="muted small">{{ KIND[selected.kind] || selected.kind }}<template v-if="selected.estimated"> · estimated from an IP address</template></div>
        <dl>
          <template v-if="selected.ip"><dt>IP</dt><dd>{{ selected.ip }}</dd></template>
          <template v-if="selected.mac"><dt>MAC</dt><dd>{{ selected.mac }}</dd></template>
          <template v-if="selected.vendor"><dt>Made by</dt><dd>{{ selected.vendor }}</dd></template>
          <template v-if="selected.owner"><dt>Owner</dt><dd>{{ selected.owner }}</dd></template>
          <template v-if="selected.status"><dt>Status</dt><dd>{{ selected.status === "heard" ? "heard on the network, not on SIT-AIOPS" : selected.status }}</dd></template>
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
.legend .k-hub { background: var(--c-viz); } .legend .k-gateway { background: var(--c-gauge); } .legend .k-connected { background: var(--c-ok); }
.legend .k-service { background: var(--c-primary); border-radius: 50%; } .legend .k-internet { background: var(--c-primary); }
.stage { position: relative; isolation: isolate; height: calc(100vh - 230px); min-height: 460px; border-radius: var(--radius-lg);
  background:
    radial-gradient(70% 60% at 18% 10%, color-mix(in srgb, var(--c-gauge) 8%, transparent), transparent 72%),
    radial-gradient(62% 55% at 84% 86%, color-mix(in srgb, var(--c-viz) 8%, transparent), transparent 74%),
    var(--surface);
  box-shadow: var(--shadow-1); overflow: hidden; }
.stage::after { content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none;
  background: linear-gradient(180deg, color-mix(in srgb, var(--c-text) 2%, transparent), transparent 22%, color-mix(in srgb, var(--c-bg) 18%, transparent)); }
.canvas { position: absolute; inset: 0; }
.canvas :deep(canvas) { display: block; cursor: grab; touch-action: none; }
.canvas :deep(canvas:active) { cursor: grabbing; }
.canvas :deep(.t3-labels) { position: absolute; top: 0; left: 0; pointer-events: none; }
.canvas :deep(.t3-label) { font: 600 12px/1.2 var(--font, inherit); color: var(--c-text);
  background: color-mix(in srgb, var(--c-surface) 88%, transparent); padding: 3px 7px;
  border: 1px solid color-mix(in srgb, var(--c-text) 8%, transparent);
  border-radius: 7px; box-shadow: 0 8px 20px -14px rgba(0, 0, 0, 0.85); white-space: nowrap; }
.canvas :deep(.t3-label.service) { font-weight: 500; font-size: 11px; color: var(--c-text-2); }
.canvas :deep(.t3-label.hub) { background: var(--c-viz); color: #fff; }
.canvas :deep(.t3-label.t3-hover) { background: var(--c-text); color: var(--c-bg); font-weight: 600; }
.bar .search { display: flex; align-items: center; gap: 8px; min-width: 260px; }
.bar .search :deep(.ui-field) { margin: 0; flex: 1; } .bar .search :deep(label) { display: none; }
.nogl { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center; gap: 8px; text-align: center; }
.panel { position: absolute; top: 14px; right: 14px; width: 280px;
  background: color-mix(in srgb, var(--c-surface) 92%, transparent); border: 1px solid var(--c-border); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-2, var(--shadow-1)); padding: 14px 16px; backdrop-filter: blur(14px); }
.ptitle { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.ptitle b { font-size: var(--fs-lg); overflow-wrap: anywhere; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 12px 0; font-size: var(--fs-sm); }
dt { color: var(--c-text-3); } dd { margin: 0; overflow-wrap: anywhere; }
@media (max-width: 760px) {
  .stage { height: calc(100dvh - 250px); min-height: 430px; }
  .panel { left: 10px; right: 10px; width: auto; top: auto; bottom: 10px; }
  .legend { margin-left: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .canvas :deep(canvas) { scroll-behavior: auto; }
}
</style>
