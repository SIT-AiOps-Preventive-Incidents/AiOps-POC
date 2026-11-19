<script setup>
// A number that is also a door: a gradient card in its own colour, the figure large and white, a play button that
// says "open this", and a tone-on-tone drawing bleeding off the corner that hints at what the number counts
// (a rack of servers, radar rings, a plug on its cable, a field of dots, a mesh of nodes).
defineProps({ label: String, value: [String, Number], unit: String, sub: String, to: [String, Object],
  theme: { type: String, default: "violet" },   // violet | green | blue | rose | indigo | amber
  motif: { type: String, default: "dots" } });  // rack | radar | plug | dots | mesh
</script>
<template>
  <component :is="to ? 'router-link' : 'div'" :to="to" :class="['sc', `sc--${theme}`]">
    <span class="sc__head">
      <span class="sc__label">{{ label }}</span>
      <span v-if="to" class="sc__go" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M9.5 7.8v8.4l6.6-4.2z" fill="currentColor" /></svg></span>
    </span>
    <span class="sc__value">{{ value }}<small v-if="unit">{{ unit }}</small></span>
    <span v-if="sub" class="sc__sub">{{ sub }}</span>

    <svg class="sc__art" viewBox="0 0 160 120" aria-hidden="true">
      <!-- a rack: server units stacked like a skyline -->
      <g v-if="motif === 'rack'" fill="none" stroke="#fff" stroke-width="2.2">
        <rect x="78" y="34" width="34" height="18" rx="3" /><rect x="78" y="56" width="34" height="18" rx="3" /><rect x="78" y="78" width="34" height="18" rx="3" />
        <rect x="78" y="100" width="34" height="18" rx="3" /><rect x="118" y="12" width="30" height="16" rx="3" /><rect x="118" y="32" width="30" height="16" rx="3" />
        <rect x="118" y="52" width="30" height="16" rx="3" /><rect x="118" y="72" width="30" height="16" rx="3" /><rect x="118" y="92" width="30" height="16" rx="3" />
        <path d="M84 43h12M84 65h12M84 87h12M124 20h10M124 40h10M124 60h10M124 80h10" stroke-linecap="round" />
        <circle cx="105" cy="43" r="2.4" fill="#fff" /><circle cx="141" cy="40" r="2.4" fill="#fff" />
      </g>
      <!-- radar: rings around a found blip -->
      <g v-else-if="motif === 'radar'" fill="none" stroke="#fff" stroke-width="2.2">
        <circle cx="132" cy="96" r="22" /><circle cx="132" cy="96" r="42" /><circle cx="132" cy="96" r="62" stroke-dasharray="4 7" />
        <path d="M132 96L98 58" stroke-linecap="round" /><path d="M132 96L98 58A50 50 0 0 1 132 46z" fill="#fff" fill-opacity=".35" stroke="none" />
        <circle cx="104" cy="70" r="5" fill="#fff" />
      </g>
      <!-- a plug on a curling cable, waiting to be connected -->
      <g v-else-if="motif === 'plug'" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round">
        <path d="M150 120c-20-8-10-32-28-38s-28 14-44 4-4-30 6-36" />
        <path d="M84 50c6-4 14-2 16 4" />
        <rect x="102" y="18" width="22" height="20" rx="6" fill="#fff" fill-opacity=".3" />
        <path d="M108 18V8M118 18V8M113 38v8" />
        <circle cx="86" cy="98" r="4" fill="#fff" /><circle cx="140" cy="62" r="3" fill="#fff" />
      </g>
      <!-- a field of dots rising to the corner: the ones that need you -->
      <g v-else-if="motif === 'dots'" fill="#fff">
        <template v-for="r in 6" :key="r"><circle v-for="c in r" :key="c" :cx="158 - (c - 1) * 15" :cy="118 - (6 - r) * 15 - (r - 1) * 0"
          :r="5.2" :opacity="0.25 + (c === 1 ? 0.35 : 0)" /></template>
      </g>
      <!-- a mesh: networks joined by their gateways -->
      <g v-else fill="none" stroke="#fff" stroke-width="2.2">
        <path d="M84 98L110 70L146 84L128 40L110 70M84 98L126 116M146 84L126 116M128 40L154 22" />
        <circle cx="84" cy="98" r="6" fill="#fff" fill-opacity=".35" /><circle cx="110" cy="70" r="8" fill="#fff" fill-opacity=".45" />
        <circle cx="146" cy="84" r="6" fill="#fff" fill-opacity=".35" /><circle cx="128" cy="40" r="6" fill="#fff" fill-opacity=".35" />
        <circle cx="126" cy="116" r="5" fill="#fff" fill-opacity=".35" /><circle cx="154" cy="22" r="4" fill="#fff" />
      </g>
    </svg>
  </component>
</template>
<style scoped>
.sc { position: relative; overflow: hidden; isolation: isolate; display: flex; flex-direction: column; min-height: 168px; padding: 22px 24px;
  border-radius: 24px; color: #fff; text-decoration: none; background: var(--g); box-shadow: 0 16px 34px -18px var(--glow), inset 0 1px 0 rgba(255, 255, 255, 0.22);
  transition: transform var(--dur) var(--ease), box-shadow var(--dur) var(--ease); }
a.sc:hover { transform: translateY(-3px); box-shadow: 0 22px 40px -16px var(--glow), inset 0 1px 0 rgba(255, 255, 255, 0.22); }
.sc__head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
.sc__label { font-size: 19px; font-weight: var(--fw-semibold); line-height: 1.2; letter-spacing: -0.01em; max-width: 12ch; }
.sc__go { width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center; flex: none; background: rgba(255, 255, 255, 0.24);
  transition: background var(--dur-fast) var(--ease), transform var(--dur) var(--ease); }
.sc__go svg { width: 18px; height: 18px; }
a.sc:hover .sc__go { background: rgba(255, 255, 255, 0.36); transform: scale(1.08); }
.sc__value { margin-top: auto; font-size: 54px; font-weight: var(--fw-bold); letter-spacing: -0.04em; line-height: 1; font-variant-numeric: tabular-nums; }
.sc__value small { font-size: 16px; font-weight: var(--fw-medium); letter-spacing: 0; margin-left: 6px; opacity: 0.85; }
.sc__sub { margin-top: 6px; font-size: var(--fs-sm); opacity: 0.82; }
.sc__art { position: absolute; right: -6px; bottom: -6px; width: 62%; height: 82%; z-index: -1; opacity: 0.26; transition: transform var(--dur) var(--ease); }
a.sc:hover .sc__art { transform: translate(-3px, -3px); }
/* gradients: rich but not neon; each has its own soft glow */
.sc--violet { --g: linear-gradient(150deg, #cc84c2 0%, #9a57b0 55%, #7c429d 100%); --glow: rgba(156, 87, 176, 0.75); }
.sc--green  { --g: linear-gradient(160deg, #93d6a4 0%, #64c27a 55%, #49a962 100%); --glow: rgba(90, 190, 115, 0.7); }
.sc--blue   { --g: linear-gradient(150deg, #8ad3e3 0%, #6aa5d6 50%, #4b74c2 100%); --glow: rgba(80, 140, 210, 0.75); }
.sc--rose   { --g: linear-gradient(160deg, #ea8a90 0%, #c4567c 55%, #96296f 100%); --glow: rgba(200, 80, 120, 0.75); }
.sc--indigo { --g: linear-gradient(150deg, #8fa8f2 0%, #6f78e0 55%, #5a52c4 100%); --glow: rgba(110, 115, 225, 0.7); }
.sc--amber  { --g: linear-gradient(150deg, #f5c77e 0%, #ec9f55 55%, #d97a3a 100%); --glow: rgba(230, 150, 80, 0.7); }
@media (prefers-reduced-motion: reduce) { .sc, .sc__art, .sc__go { transition: none; } }
</style>
