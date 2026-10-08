<script setup>
import { computed } from "vue";
import UiIcon from "./UiIcon.vue";

const props = defineProps({ to: [String, Object], title: String, subtitle: String, detail: String, chevron: { type: Boolean, default: undefined } });
const emit = defineEmits(["click"]);
const showChevron = computed(() => props.chevron ?? !!props.to);
</script>
<template>
  <component :is="to ? 'router-link' : 'div'" :to="to" class="ui-row" role="listitem"
             :class="{ 'ui-row--tap': to || $attrs.onClick }" @click="emit('click', $event)">
    <slot name="leading" />
    <div class="ui-row__text">
      <div class="ui-row__title"><slot name="title">{{ title }}</slot></div>
      <div v-if="subtitle || $slots.subtitle" class="ui-row__sub"><slot name="subtitle">{{ subtitle }}</slot></div>
      <div v-if="detail" class="ui-row__detail">{{ detail }}</div>
    </div>
    <div v-if="$slots.accessory" class="ui-row__acc"><slot name="accessory" /></div>
    <UiIcon v-if="showChevron" name="chevron_right" :size="16" class="ui-row__chev" />
  </component>
</template>
<style scoped>
.ui-row { display: flex; align-items: center; gap: 12px; padding: 11px 16px; min-height: 52px; position: relative; color: var(--c-text); }
.ui-row--tap { cursor: pointer; }
.ui-row--tap:hover { background: var(--c-fill); }
.ui-row__text { flex: 1; min-width: 0; }
.ui-row__title { font-weight: var(--fw-medium); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ui-row__sub { font-size: var(--fs-sm); color: var(--c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ui-row__detail { font-size: var(--fs-sm); color: var(--c-text-2); margin-top: 2px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.ui-row__acc { font-size: 14px; color: var(--c-text-2); white-space: nowrap; display: flex; align-items: center; gap: 6px; font-variant-numeric: tabular-nums; }
.ui-row__chev { color: var(--c-neutral); }
</style>
