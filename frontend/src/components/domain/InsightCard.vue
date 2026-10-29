<script setup>
// One finding from the incident history: the number, what it means for the business, the one thing to do about it,
// and how the number was worked out - so it can be trusted, or its assumption changed.
import { computed } from "vue";
const props = defineProps({ f: { type: Object, required: true } });
const SCENE = {
  approval_backlog: ["wrench", "butter", "arrow"], repeat_offender: ["inc_error", "rose", "alert"], downtime_cost: ["tag", "peach", "arrow"],
  hours_saved: ["sparkle", "mint", "check"], coverage_gap: ["vm", "sky", "plus"], weekly_trend: ["pulse", "lilac", "arrow"],
  runbook_reuse: ["book", "mint", "check"], rate_more: ["flash", "butter", "plus"], no_data: ["flash", "slate", "arrow"],
};
const scene = computed(() => SCENE[props.f.id] || ["sparkle", "sky", "arrow"]);
</script>
<template>
  <article :class="['ins', `t-${f.tone}`]">
    <div class="ins__body">
      <b class="ins__v">{{ f.value }}</b>
      <h3>{{ f.headline }}</h3>
      <p class="ins__d">{{ f.detail }}</p>
      <UiButton :to="f.action.to" size="sm" :variant="f.tone === 'action' ? 'primary' : 'tint'" chevron class="ins__go">{{ f.action.label }}</UiButton>
      <p class="ins__basis"><span>How this is worked out</span>{{ f.basis }}</p>
    </div>
    <UiSpot :glyph="scene[0]" :hue="scene[1]" :badge="scene[2]" :size="92" class="ins__art" />
  </article>
</template>
<style scoped>
.ins { position: relative; overflow: hidden; display: flex; gap: 12px; padding: 22px 20px 20px 24px; border-radius: 20px; background: var(--surface);
  box-shadow: var(--shadow-card); isolation: isolate; }
/* a soft wash of the finding's colour from the top-left: the eye finds the urgent ones first */
.ins::before { content: ""; position: absolute; inset: 0; z-index: -1; opacity: 0.16;
  background: radial-gradient(110% 80% at 0% 0%, var(--wash), transparent 60%); }
.t-action { --wash: var(--c-action); --val: var(--c-action-text); } .t-bad { --wash: var(--c-bad); --val: var(--c-bad-text); }
.t-warn { --wash: var(--c-warn); --val: var(--c-warn-text); } .t-ok { --wash: var(--c-ok); --val: var(--c-ok-text); }
.t-info { --wash: var(--c-info); --val: var(--c-info-text); } .t-neutral { --wash: var(--c-text-3); --val: var(--c-text); }
.ins__body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.ins__v { font-size: 40px; font-weight: var(--fw-bold); letter-spacing: -0.035em; line-height: 1; color: var(--val); font-variant-numeric: tabular-nums; }
.ins h3 { font-size: 17px; font-weight: var(--fw-semibold); letter-spacing: -0.01em; margin-top: 4px; }
.ins__d { font-size: var(--fs-sm); color: var(--c-text-2); line-height: 1.5; max-width: 52ch; }
.ins__go { align-self: flex-start; margin-top: 10px; }
.ins__basis { font-size: var(--fs-xs); color: var(--c-text-3); margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--c-separator); line-height: 1.45; }
.ins__basis span { display: block; font-size: 10px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.09em; margin-bottom: 2px; }
.ins__art { align-self: flex-start; }
@media (max-width: 560px) { .ins__art { display: none; } }
</style>
