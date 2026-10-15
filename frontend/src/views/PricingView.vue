<script setup>
// Pricing: three plans built from what the product actually does. Blue marks the recommended plan,
// orange is kept for "your turn" moments only, so it is used sparingly here (the headline verb).
import { computed, ref } from "vue";
const cycle = ref("yearly");
const yearly = computed(() => cycle.value === "yearly");
const PLANS = [
  {
    id: "free", name: "Starter", tagline: "One team trying AIOps on a few machines.",
    monthly: 0, yearly: 0, unit: "forever", cta: "Start free", to: "/connect", primary: false,
    features: ["Up to 10 monitored machines", "Host health + service discovery", "Service map and Fleet map",
      "Agentic root-cause analysis", "Every fix needs your approval", "8 days of history", "Community support"],
  },
  {
    id: "team", name: "Team", tagline: "Teams running a real fleet of VMs or cloud instances.",
    monthly: 12, yearly: 9, unit: "per monitored host / month", cta: "Start free trial", to: "/connect", primary: true,
    features: ["Everything in Starter, no machine limit", "eBPF auto-tracing (logs, metrics, traces)",
      "Bulk connect across the fleet", "Hypervisor view (Proxmox) + blast radius", "Cross-VM root cause",
      "90 days of history", "Microsoft Teams / Slack alerts", "Email support"],
  },
  {
    id: "enterprise", name: "Enterprise", tagline: "Many teams, strict control, on-prem or air-gapped.",
    monthly: null, yearly: null, unit: "custom", cta: "Talk to us", to: "/settings", primary: false,
    features: ["Everything in Team", "SSO and role-based access", "On-prem / air-gapped deployment",
      "Audit log export", "Custom runbooks and AI skills", "Uptime SLA", "Dedicated support"],
  },
];
const price = (p) => (p.monthly == null ? "Custom" : p.monthly === 0 ? "$0" : `$${yearly.value ? p.yearly : p.monthly}`);
const FAQ = [
  ["What counts as a monitored host?", "Any computer, server or VM with the AIOps agent reporting. Machines you only discover on the network but do not monitor are free."],
  ["Does the AI change anything on its own?", "No. The AI finds the cause and tests a fix in a dry run, but nothing is applied until a person approves — on every plan."],
  ["Can we self-host?", "Yes. Starter and Team run in your own environment; Enterprise adds air-gapped and SSO. Your telemetry never has to leave your network."],
];
</script>
<template>
  <div class="page">
    <UiPageHeader title="Pricing" subtitle="Start free. Pay only for the machines you actually monitor — discovery and the Fleet map are always free." />

    <div class="billing">
      <UiSegmented v-model="cycle" :options="[{ value: 'monthly', label: 'Monthly' }, { value: 'yearly', label: 'Yearly · save 25%' }]" label="Billing period" />
    </div>

    <div class="plans">
      <section v-for="p in PLANS" :key="p.id" :class="['plan', { 'plan--primary': p.primary }]">
        <div v-if="p.primary" class="plan__tag">Recommended</div>
        <h2 class="plan__name">{{ p.name }}</h2>
        <p class="plan__tag-line">{{ p.tagline }}</p>
        <div class="plan__price"><b>{{ price(p) }}</b><span>{{ p.unit }}</span></div>
        <UiButton :variant="p.primary ? 'primary' : 'tint'" block :to="p.to">{{ p.cta }}</UiButton>
        <ul class="plan__feat">
          <li v-for="f in p.features" :key="f">
            <UiIcon name="checkmark_circle" filled :size="17" /><span>{{ f }}</span>
          </li>
        </ul>
      </section>
    </div>

    <p class="note muted small">Prices are per monitored host and shown in USD. Billed {{ yearly ? "yearly" : "monthly" }}; cancel anytime. A capstone demo — figures are illustrative.</p>

    <div class="section-label">Questions</div>
    <UiList plain>
      <UiListRow v-for="[q, a] in FAQ" :key="q" :title="q" :subtitle="a" />
    </UiList>
  </div>
</template>
<style scoped>
.billing { display: flex; justify-content: center; margin-bottom: var(--sp-6); }
.plans { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--sp-4); align-items: start; }
.plan { position: relative; background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-xl); padding: var(--sp-6); display: flex; flex-direction: column; gap: var(--sp-3); }
.plan--primary { border-color: var(--c-primary); box-shadow: 0 0 0 1px var(--c-primary), 0 12px 32px color-mix(in srgb, var(--c-primary) 14%, transparent); }
.plan__tag { position: absolute; top: -12px; left: var(--sp-6); background: var(--c-primary); color: var(--c-on-primary); font-size: var(--fs-xs); font-weight: var(--fw-semibold); padding: 3px 12px; border-radius: var(--radius-pill); }
.plan__name { font-size: var(--fs-2xl); font-weight: var(--fw-semibold); line-height: var(--lh-tight); }
.plan__tag-line { color: var(--c-text-2); font-size: var(--fs-sm); min-height: 2.6em; }
.plan__price { display: flex; flex-direction: column; margin: var(--sp-1) 0 var(--sp-2); }
.plan__price b { font-size: var(--fs-3xl); font-weight: var(--fw-bold); line-height: var(--lh-tight); font-variant-numeric: tabular-nums; }
.plan__price span { font-size: var(--fs-sm); color: var(--c-text-3); }
.plan__feat { list-style: none; padding: 0; margin: var(--sp-2) 0 0; display: grid; gap: var(--sp-2); }
.plan__feat li { display: flex; align-items: flex-start; gap: var(--sp-2); font-size: var(--fs-sm); color: var(--c-text); }
.plan__feat .ui-icon { color: var(--c-ok); flex: none; margin-top: 1px; }
.plan--primary .plan__feat .ui-icon { color: var(--c-primary); }
.note { margin: var(--sp-4) 0 var(--sp-2); text-align: center; }
@media (max-width: 860px) { .plans { grid-template-columns: 1fr; } .plan__tag-line { min-height: 0; } }
</style>
