<script setup>
// One thing you run, in a list: a picture of what it is (a drawn glyph, or the real logo), its name, a line of facts,
// a quiet third line, then whatever the page puts on the right (numbers, a health mark, an action) and a chevron
// when the row opens something. Services, hosts and fleet machines all use it, so every list reads the same.
import UiGlyph from "./UiGlyph.vue";
import UiIcon from "./UiIcon.vue";
import UiLogo from "./UiLogo.vue";
defineProps({ to: [String, Object], title: String, subtitle: String, meta: String, glyph: { type: String, default: "service" },
  logo: String, tone: String, accent: Boolean }); // tone: corner dot on the tile; accent: thin mint edge (your turn)
</script>
<template>
  <component :is="to ? 'router-link' : 'div'" :to="to" :class="['rr', { 'rr--link': to, 'rr--accent': accent }]" role="listitem">
    <span class="rr__tile">
      <UiLogo v-if="logo" :name="logo" :size="26" />
      <UiGlyph v-else :name="glyph" :size="28" />
      <span v-if="tone" :class="['rr__dot', `t-${tone}`]" />
    </span>
    <span class="rr__main">
      <span class="rr__title">{{ title }}<slot name="title-after" /></span>
      <span v-if="subtitle" class="rr__sub">{{ subtitle }}</span>
      <span v-if="meta" class="rr__meta">{{ meta }}</span>
    </span>
    <span v-if="$slots.default" class="rr__aside"><slot /></span>
    <UiIcon v-if="to" name="chevron_right" :size="16" class="rr__go" />
  </component>
</template>
<style scoped>
.rr { position: relative; display: flex; align-items: center; gap: 16px; padding: 14px 20px; color: var(--c-text); min-height: 74px; }
.rr--link { cursor: pointer; transition: background var(--dur-fast) var(--ease); }
.rr--link:hover { background: var(--c-hover); }
.rr--link:hover .rr__go { color: var(--c-text); transform: translateX(2px); }
.rr--accent::before { content: ""; position: absolute; left: 0; top: 14px; bottom: 14px; width: 3px; border-radius: 0 3px 3px 0; background: var(--c-action); }
.rr__tile { position: relative; width: 46px; height: 46px; flex: none; border-radius: 14px; display: grid; place-items: center; background: var(--c-fill);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.05); }
.rr__dot { position: absolute; right: -2px; bottom: -2px; width: 12px; height: 12px; border-radius: 50%; border: 2.5px solid var(--c-surface); background: var(--c-neutral); }
.t-ok { background: var(--c-ok); } .t-bad { background: var(--c-bad); } .t-warn { background: var(--c-warn); } .t-info { background: var(--c-info); }
.rr__main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.rr__title { font-size: 15px; font-weight: var(--fw-semibold); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rr__sub { font-size: var(--fs-sm); color: var(--c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.rr__meta { font-size: var(--fs-xs); color: var(--c-text-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-variant-numeric: tabular-nums; }
.rr__aside { display: flex; align-items: center; gap: 22px; flex: none; }
.rr__go { color: var(--c-text-3); flex: none; transition: transform var(--dur-fast) var(--ease), color var(--dur-fast) var(--ease); }
@media (max-width: 760px) { .rr { padding: 12px 14px; gap: 12px; } .rr__tile { width: 40px; height: 40px; } .rr__aside { gap: 12px; } }
</style>
