<script setup>
// The shape of a page before its data arrives: a header, then cards (dashboard), rows (list) or a detail layout.
// It holds the layout still, so nothing jumps when the numbers land, and says "loading" to screen readers once.
import UiSkeleton from "./UiSkeleton.vue";
defineProps({ variant: { type: String, default: "list" }, rows: { type: Number, default: 6 }, header: { type: Boolean, default: true } });
</script>
<template>
  <div class="skp" role="status" aria-live="polite" aria-label="Loading">
    <div v-if="header" class="skp__head"><UiSkeleton w="80px" h="13px" /><UiSkeleton w="240px" h="34px" r="10px" /><UiSkeleton w="min(520px, 80%)" h="13px" /></div>

    <div v-if="variant === 'dashboard'" class="skp__board">
      <div class="skp__card skp__card--tall"><UiSkeleton w="70px" h="13px" /><UiSkeleton w="60%" h="44px" r="12px" /><UiSkeleton w="45%" h="44px" r="12px" />
        <div class="skp__push"><UiSkeleton v-for="i in 4" :key="i" w="70%" h="12px" /></div></div>
      <div v-for="i in 4" :key="i" class="skp__card">
        <div class="skp__row"><div class="skp__col"><UiSkeleton w="60%" h="20px" r="8px" /><UiSkeleton w="40%" h="12px" /></div><UiSkeleton w="72px" h="72px" r="50%" /></div>
        <UiSkeleton w="100%" h="5px" r="3px" />
      </div>
    </div>

    <div v-else-if="variant === 'detail'" class="skp__detail">
      <div class="skp__card"><div class="skp__steps"><UiSkeleton v-for="i in 5" :key="i" w="22%" h="10px" r="5px" /></div></div>
      <div class="skp__split">
        <div class="skp__card skp__col"><UiSkeleton w="30%" h="18px" /><UiSkeleton w="90%" h="13px" /><UiSkeleton w="80%" h="13px" /><UiSkeleton w="85%" h="13px" /><UiSkeleton w="60%" h="13px" /></div>
        <div class="skp__card skp__col"><UiSkeleton w="45%" h="18px" /><UiSkeleton w="100%" h="56px" r="12px" /><UiSkeleton w="100%" h="40px" r="10px" /></div>
      </div>
    </div>

    <div v-else class="skp__list">
      <div v-for="i in rows" :key="i" class="skp__item">
        <UiSkeleton w="46px" h="46px" r="14px" />
        <div class="skp__col skp__grow"><UiSkeleton :w="`${40 + ((i * 17) % 35)}%`" h="15px" /><UiSkeleton :w="`${55 + ((i * 23) % 30)}%`" h="12px" /><UiSkeleton w="22%" h="10px" /></div>
        <UiSkeleton w="96px" h="14px" />
      </div>
    </div>
  </div>
</template>
<style scoped>
.skp { display: flex; flex-direction: column; gap: 20px; }
.skp__head { display: flex; flex-direction: column; gap: 10px; padding: 16px 0 8px; }
.skp__card { background: var(--surface); box-shadow: var(--shadow-card); border-radius: 20px; padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.skp__board { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
.skp__card--tall { grid-row: span 2; min-height: 360px; }
.skp__push { margin-top: auto; display: flex; flex-direction: column; gap: 14px; }
.skp__row { display: flex; justify-content: space-between; gap: 16px; }
.skp__col { display: flex; flex-direction: column; gap: 10px; }
.skp__grow { flex: 1; min-width: 0; }
.skp__steps { display: flex; justify-content: space-between; gap: 12px; }
.skp__split { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: 16px; }
.skp__list { background: var(--surface); box-shadow: var(--shadow-card); border-radius: 20px; overflow: hidden; }
.skp__item { display: flex; align-items: center; gap: 16px; padding: 14px 20px; min-height: 74px; }
.skp__item + .skp__item { border-top: 1px solid var(--c-separator); }
@media (max-width: 1080px) { .skp__board { grid-template-columns: 1fr 1fr; } .skp__split { grid-template-columns: 1fr; } }
@media (max-width: 640px) { .skp__board { grid-template-columns: 1fr; } }
</style>
