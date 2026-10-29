<script setup>
// Pastel glyphs for everything that names a thing (navigation, connect choices, lists, incident kinds), finished to
// look drawn by a person rather than generated: the colour is printed slightly off the line (like a riso print),
// the colour carries a fine paper grain, and a thin plum pen line - never black - traces each shape with a small
// wobble and the odd gap where the pen lifted. The shapes themselves are three tones of one soft hue.
import { computed, useId } from "vue";
const props = defineProps({ name: { type: String, required: true }, size: { type: Number, default: 22 } });
const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
// a stable "hand" per glyph name, so the same icon always wobbles the same way
const seed = computed(() => [...props.name].reduce((a, c) => (a * 31 + c.charCodeAt(0)) % 997, 7));
// small icons get a gentler wobble, or the line turns to noise
const rough = computed(() => (props.size < 24 ? 0.55 : props.size < 40 ? 0.8 : 1.1));
</script>
<template>
  <svg class="ui-glyph" :width="size" :height="size" viewBox="-1 -1 26 26" aria-hidden="true">
    <defs>
      <filter :id="`${id}w`" x="-10%" y="-10%" width="120%" height="120%">
        <feTurbulence type="fractalNoise" baseFrequency="0.09" numOctaves="2" :seed="seed" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" :scale="rough" xChannelSelector="R" yChannelSelector="G" />
      </filter>
      <filter :id="`${id}g`" x="-10%" y="-10%" width="120%" height="120%">
        <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" :seed="seed + 3" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" :scale="rough * 0.7" xChannelSelector="R" yChannelSelector="G" result="d" />
        <feTurbulence type="fractalNoise" baseFrequency="1.4" numOctaves="1" :seed="seed + 9" result="grain" />
        <feColorMatrix in="grain" type="matrix" values="0 0 0 0 0.24  0 0 0 0 0.2  0 0 0 0 0.32  0 0 0 -2.2 0.62" result="specks" />
        <feComposite in="specks" in2="d" operator="in" result="sp" />
        <feMerge><feMergeNode in="d" /><feMergeNode in="sp" /></feMerge>
      </filter>
      <g :id="`${id}a`">
    <!-- overview: a dashboard panel, two tiles and a dial -->
    <g v-if="name === 'home'">
      <rect x="2" y="3.5" width="20" height="17" rx="4.5" fill="#acdcf3" />
      <rect x="2" y="3.5" width="20" height="4" rx="2" fill="#e2f3fc" opacity=".55" />
      <rect x="4.5" y="9" width="6" height="4" rx="1.4" fill="#e2f3fc" />
      <rect x="4.5" y="14.5" width="6" height="3.5" rx="1.4" fill="#e2f3fc" />
      <path d="M13.5 17a3.5 3.5 0 0 1 7 0" fill="none" stroke="#3d7fa8" stroke-width="1.4" stroke-linecap="round" />
      <path d="M17 17l1.5-2" stroke="#efa274" stroke-width="1.4" stroke-linecap="round" />
    </g>
    <!-- incidents: a soft triangle -->
    <g v-else-if="name === 'warning'">
      <path d="M10.2 4.2a2.1 2.1 0 0 1 3.6 0l7.6 13.2a2.1 2.1 0 0 1-1.8 3.1H4.4a2.1 2.1 0 0 1-1.8-3.1z" fill="#f6e29a" />
      <path d="M12 3.2c.7 0 1.4.4 1.8 1l7.6 13.2c.4.7.4 1.5 0 2.1L12 3.2z" fill="#e9c55b" />
      <rect x="11.1" y="8.5" width="1.8" height="6" rx=".9" fill="#9a7a1e" />
      <circle cx="12" cy="17" r="1.1" fill="#9a7a1e" />
    </g>
    <!-- fleet / server: a two-unit rack -->
    <g v-else-if="name === 'server'">
      <rect x="4" y="3" width="16" height="8" rx="2.6" fill="#cdd4df" />
      <rect x="4" y="13" width="16" height="8" rx="2.6" fill="#cdd4df" />
      <rect x="4" y="3" width="16" height="3" rx="1.5" fill="#eef1f5" opacity=".7" />
      <rect x="4" y="13" width="16" height="3" rx="1.5" fill="#eef1f5" opacity=".7" />
      <path d="M7 7.6h5M7 17.6h5" stroke="#5d6a7e" stroke-width="1.2" stroke-linecap="round" />
      <circle cx="16.5" cy="7.6" r="1.2" fill="#6cc8a0" /><circle cx="16.5" cy="17.6" r="1.2" fill="#6cc8a0" />
    </g>
    <!-- service map: three linked nodes -->
    <g v-else-if="name === 'flowchart'">
      <path d="M7 7.5L17 11M7 7.5l3 10.5M17 11l-7 7" stroke="#9ea9ba" stroke-width="1.1" />
      <circle cx="6.5" cy="7" r="3.6" fill="#acdcf3" /><circle cx="5.6" cy="6.1" r="1.3" fill="#e2f3fc" />
      <circle cx="17.5" cy="11" r="3.6" fill="#a9e5c9" /><circle cx="16.6" cy="10.1" r="1.3" fill="#e3f7ee" />
      <circle cx="10" cy="18" r="3.6" fill="#f9cba9" /><circle cx="9.1" cy="17.1" r="1.3" fill="#feebdd" />
    </g>
    <!-- services (cube): an isometric box -->
    <g v-else-if="name === 'cube'">
      <path d="M12 2.8l8.5 4.7L12 12.2 3.5 7.5z" fill="#eee8fd" />
      <path d="M3.5 7.5L12 12.2v9.3l-8.5-4.7z" fill="#cbbcf4" />
      <path d="M20.5 7.5L12 12.2v9.3l8.5-4.7z" fill="#a28be3" />
    </g>
    <!-- runbooks: a closed book with a ribbon -->
    <g v-else-if="name === 'book'">
      <path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H19v17H7.5A2.5 2.5 0 0 0 5 21.5z" fill="#a9e5c9" />
      <path d="M5 21.5A2.5 2.5 0 0 1 7.5 19H19v3H7.5A2.5 2.5 0 0 1 5 21.5z" fill="#e3f7ee" />
      <path d="M5 4.5A2.5 2.5 0 0 1 7.5 2H9v17H7.5A2.5 2.5 0 0 0 5 21.5z" fill="#6cc8a0" />
      <path d="M13 2v6.5l1.8-1.3 1.8 1.3V2" fill="#f6e29a" />
    </g>
    <!-- AI skills: a chip with a spark -->
    <g v-else-if="name === 'sparkle'">
      <rect x="3.5" y="9" width="12" height="12" rx="3" fill="#acdcf3" />
      <rect x="6.5" y="12" width="6" height="6" rx="1.5" fill="#e2f3fc" />
      <path d="M18 2l1.3 3.2 3.2 1.3-3.2 1.3L18 11l-1.3-3.2-3.2-1.3 3.2-1.3z" fill="#f6e29a" />
      <path d="M18 4.5l.5 1.5 1.5.5-1.5.5-.5 1.5-.5-1.5-1.5-.5 1.5-.5z" fill="#fdf6d8" />
    </g>
    <!-- connect: a plug -->
    <g v-else-if="name === 'plug'">
      <rect x="7.6" y="2" width="1.8" height="5.5" rx=".9" fill="#9ea9ba" />
      <rect x="14.6" y="2" width="1.8" height="5.5" rx=".9" fill="#9ea9ba" />
      <path d="M5.5 7h13v4a6.5 6.5 0 0 1-13 0z" fill="#a9e5c9" />
      <path d="M5.5 7h13v2h-13z" fill="#e3f7ee" />
      <rect x="11" y="16.5" width="2" height="5.5" rx="1" fill="#6cc8a0" />
      <circle cx="12" cy="11.5" r="1.2" fill="#2f8a64" />
    </g>
    <!-- notifications: a bell -->
    <g v-else-if="name === 'alert'">
      <path d="M12 2.8a6.2 6.2 0 0 0-6.2 6.2v4.2L4 16.6h16l-1.8-3.4V9A6.2 6.2 0 0 0 12 2.8z" fill="#f9cba9" />
      <path d="M12 2.8A6.2 6.2 0 0 1 18.2 9v4.2l1.8 3.4h-5.5C16 12 15.5 6 12 2.8z" fill="#efa274" opacity=".55" />
      <path d="M9.5 18.2a2.5 2.5 0 0 0 5 0z" fill="#efa274" />
      <circle cx="18.2" cy="5" r="2.6" fill="#f5b6c2" />
    </g>
    <!-- settings: a gear -->
    <g v-else-if="name === 'settings'">
      <path d="M10.4 2.5h3.2l.5 2.4 1.9.8 2-1.4 2.3 2.3-1.4 2 .8 1.9 2.4.5v3.2l-2.4.5-.8 1.9 1.4 2-2.3 2.3-2-1.4-1.9.8-.5 2.4h-3.2l-.5-2.4-1.9-.8-2 1.4-2.3-2.3 1.4-2-.8-1.9-2.4-.5v-3.2l2.4-.5.8-1.9-1.4-2 2.3-2.3 2 1.4 1.9-.8z" fill="#cdd4df" />
      <circle cx="12" cy="12" r="4.6" fill="#eef1f5" />
      <circle cx="12" cy="12" r="2.2" fill="#9ea9ba" />
    </g>
    <!-- cloud: a cloud holding a small server -->
    <g v-else-if="name === 'cloud'">
      <path d="M7 19.5h10.5a4.5 4.5 0 0 0 .8-8.9 6.3 6.3 0 0 0-12.1-1.4A5.2 5.2 0 0 0 7 19.5z" fill="#acdcf3" />
      <path d="M8 9.6A5.5 5.5 0 0 1 17.3 8" fill="none" stroke="#e2f3fc" stroke-width="1.4" stroke-linecap="round" />
      <rect x="8.5" y="12.2" width="7" height="4.4" rx="1.3" fill="#e2f3fc" />
      <circle cx="10.4" cy="14.4" r=".9" fill="#6cc8a0" />
      <path d="M12.3 14.4h1.6" stroke="#3d7fa8" stroke-width="1" stroke-linecap="round" />
    </g>
    <!-- demo: a lightning bolt -->
    <g v-else-if="name === 'flash'">
      <path d="M13.8 2L5 13.6h6.2L9.8 22l9-11.8h-6.4z" fill="#f6e29a" />
      <path d="M13.8 2l-1 8.2h6l-9 11.8 1.4-8.4z" fill="#e9c55b" opacity=".6" />
    </g>
    <!-- pricing: a tag -->
    <g v-else-if="name === 'tag'">
      <path d="M2.5 11.2V4.2a1.7 1.7 0 0 1 1.7-1.7h7l10 10a1.7 1.7 0 0 1 0 2.4l-6.6 6.6a1.7 1.7 0 0 1-2.4 0z" fill="#f5b6c2" />
      <path d="M11.2 2.5l10 10a1.7 1.7 0 0 1 0 2.4l-3.3 3.3L7 7.3l4.2-4.8z" fill="#e8889b" opacity=".45" />
      <circle cx="7.4" cy="7.4" r="1.9" fill="#fde5ea" />
    </g>
    <!-- design system: a palette -->
    <g v-else-if="name === 'color'">
      <path d="M12 2.5a9.5 9.5 0 0 0 0 19c1.4 0 2-.9 2-1.8 0-1.6-1.5-1.7-1.5-3.2 0-1 .8-1.5 1.8-1.5h2.2A5 5 0 0 0 21.5 10C21.5 5.8 17.3 2.5 12 2.5z" fill="#eef1f5" />
      <circle cx="7.5" cy="11" r="1.7" fill="#f5b6c2" /><circle cx="9.5" cy="6.8" r="1.7" fill="#f6e29a" />
      <circle cx="14.5" cy="6.5" r="1.7" fill="#a9e5c9" /><circle cx="17.5" cy="10" r="1.7" fill="#acdcf3" />
    </g>
    <!-- a computer -->
    <g v-else-if="name === 'laptop'">
      <rect x="4" y="4" width="16" height="11.5" rx="2.4" fill="#cdd4df" />
      <rect x="5.8" y="5.8" width="12.4" height="8" rx="1.3" fill="#acdcf3" />
      <path d="M7.5 8h5" stroke="#e2f3fc" stroke-width="1.2" stroke-linecap="round" />
      <path d="M2 17.5h20l-1 2.1a1.6 1.6 0 0 1-1.4.9H4.4a1.6 1.6 0 0 1-1.4-.9z" fill="#9ea9ba" />
    </g>
    <!-- a website: a globe -->
    <g v-else-if="name === 'globe'">
      <circle cx="12" cy="12" r="9.5" fill="#a9e5c9" />
      <path d="M6.5 6.8c2 .6 2.4 2.1 1.4 3.6s.5 3 2.5 3 1.5 3-.4 4.6M14.2 2.8c-.5 2 .5 3 2 3.4s2 2.6 1 4 .5 3.1 3 2.6" fill="none" stroke="#2f8a64" stroke-width="1.1" stroke-linecap="round" opacity=".6" />
      <path d="M5 8a8 8 0 0 1 6-4.8" fill="none" stroke="#e3f7ee" stroke-width="1.4" stroke-linecap="round" />
    </g>
    <!-- an app traced with OpenTelemetry: a pulse in a window -->
    <g v-else-if="name === 'pulse'">
      <rect x="2.5" y="4" width="19" height="16" rx="4" fill="#cbbcf4" />
      <rect x="2.5" y="4" width="19" height="4" rx="2" fill="#eee8fd" opacity=".6" />
      <path d="M5 14h3l2-4 3 7 2-3h4" fill="none" stroke="#6a52b8" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
    </g>
    <!-- a fix: a wrench -->
    <g v-else-if="name === 'wrench'">
      <path d="M14.5 3a5 5 0 0 0-4.7 6.7L3.6 15.9a2.1 2.1 0 0 0 3 3l6.2-6.2A5 5 0 0 0 19.5 8l-3 3-2.9-.5-.5-2.9 3-3a5 5 0 0 0-1.6-.6z" fill="#cdd4df" />
      <circle cx="5.2" cy="17.4" r="1" fill="#eef1f5" />
    </g>

    <!-- ===== resources ===== -->
    <!-- gateway / router: a puck with four arrows -->
    <g v-else-if="name === 'router'">
      <ellipse cx="12" cy="15.2" rx="9.5" ry="4.5" fill="#6fb6dc" />
      <ellipse cx="12" cy="12.6" rx="9.5" ry="4.5" fill="#acdcf3" />
      <path d="M12 10.6v-3M12 7.6l-1.2 1.2M12 7.6l1.2 1.2M8.6 12.6h-3M5.6 12.6l1.2-1M15.4 12.6h3M18.4 12.6l-1.2-1" stroke="#3d7fa8" stroke-width="1.2" stroke-linecap="round" />
    </g>
    <!-- a virtual machine: a window stacked on a host -->
    <g v-else-if="name === 'vm'">
      <rect x="2.5" y="14.5" width="19" height="6.2" rx="2.2" fill="#cdd4df" />
      <circle cx="18" cy="17.6" r="1" fill="#6cc8a0" />
      <path d="M5.5 17.6h6" stroke="#5d6a7e" stroke-width="1.1" stroke-linecap="round" />
      <rect x="5" y="3" width="14" height="10" rx="2.4" fill="#f9cba9" />
      <rect x="5" y="3" width="14" height="3" rx="1.5" fill="#efa274" />
      <path d="M8 9.5h5" stroke="#feebdd" stroke-width="1.3" stroke-linecap="round" />
    </g>
    <!-- a service: three blocks, an app made of parts -->
    <g v-else-if="name === 'service'">
      <rect x="3" y="12.5" width="8" height="8" rx="2.4" fill="#acdcf3" />
      <rect x="13" y="12.5" width="8" height="8" rx="2.4" fill="#cbbcf4" />
      <rect x="8" y="3.5" width="8" height="8" rx="2.4" fill="#a9e5c9" />
      <path d="M4.5 14h3M14.5 14h3M9.5 5h3" stroke="#fff" stroke-width="1.2" stroke-linecap="round" opacity=".6" />
    </g>
    <!-- a device we cannot name -->
    <g v-else-if="name === 'device'">
      <rect x="3" y="6.5" width="18" height="11" rx="3" fill="#cdd4df" />
      <path d="M6 10.5h7M6 13.5h4" stroke="#5d6a7e" stroke-width="1.2" stroke-linecap="round" />
      <circle cx="17" cy="12" r="1.5" fill="#f6e29a" />
    </g>
    <!-- a process found running: a gear on a window -->
    <g v-else-if="name === 'process'">
      <rect x="2.5" y="4" width="19" height="16" rx="4" fill="#cdd4df" />
      <circle cx="12" cy="12.4" r="3.8" fill="#f6e29a" /><circle cx="12" cy="12.4" r="1.5" fill="#cdd4df" />
      <path d="M12 6.8v1.4M12 16.6V18M6.4 12.4h1.4M16.2 12.4h1.4" stroke="#e9c55b" stroke-width="1.5" stroke-linecap="round" />
    </g>

    <!-- ===== incident kinds ===== -->
    <!-- failure rate: a chart line that breaks into a drop -->
    <g v-else-if="name === 'inc_error'">
      <rect x="2.5" y="3.5" width="19" height="17" rx="4" fill="#eef1f5" />
      <path d="M5 15.5l3.5-3.5 3 2 3.5-5" fill="none" stroke="#6fb6dc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M15.4 9.2l3.3 7" fill="none" stroke="#e8889b" stroke-width="1.5" stroke-linecap="round" stroke-dasharray="1.4 1.8" />
      <circle cx="18.8" cy="16.6" r="2" fill="#e8889b" />
    </g>
    <!-- slow responses: a stopwatch past the mark -->
    <g v-else-if="name === 'inc_latency'">
      <rect x="10.2" y="1.5" width="3.6" height="2.4" rx="1" fill="#9ea9ba" />
      <circle cx="12" cy="13" r="8.6" fill="#f9cba9" />
      <circle cx="12" cy="13" r="6.4" fill="#feebdd" />
      <path d="M12 13V6.6A6.4 6.4 0 0 1 17.7 10z" fill="#f5b6c2" />
      <path d="M12 13l3.4-3" stroke="#b9643a" stroke-width="1.5" stroke-linecap="round" />
      <circle cx="12" cy="13" r="1.1" fill="#b9643a" />
    </g>
    <!-- CPU: a chip running hot -->
    <g v-else-if="name === 'inc_cpu'">
      <path d="M8 2.5v3M12 2.5v3M16 2.5v3M8 18.5v3M12 18.5v3M16 18.5v3M2.5 8h3M2.5 12h3M2.5 16h3M18.5 8h3M18.5 12h3M18.5 16h3" stroke="#9ea9ba" stroke-width="1.3" stroke-linecap="round" />
      <rect x="5" y="5" width="14" height="14" rx="3" fill="#cdd4df" />
      <rect x="8.4" y="8.4" width="7.2" height="7.2" rx="1.8" fill="#f5b6c2" />
      <path d="M10.6 13.6c0-1.4 1.4-1.6 1.4-3 .9.6 1.4 1.6 1.4 2.4a1.4 1.4 0 0 1-2.8.6z" fill="#fde5ea" />
    </g>
    <!-- memory: a RAM stick, its cells full -->
    <g v-else-if="name === 'inc_mem'">
      <path d="M2.5 8.8A1.8 1.8 0 0 1 4.3 7h15.4a1.8 1.8 0 0 1 1.8 1.8V15h-19z" fill="#a9e5c9" />
      <path d="M4.5 15v2.4M7.5 15v2.4M10.5 15v2.4M13.5 15v2.4M16.5 15v2.4M19.5 15v2.4" stroke="#e9c55b" stroke-width="1.3" stroke-linecap="round" />
      <rect x="5" y="9.3" width="3" height="3.6" rx=".8" fill="#e8889b" /><rect x="9" y="9.3" width="3" height="3.6" rx=".8" fill="#e8889b" />
      <rect x="13" y="9.3" width="3" height="3.6" rx=".8" fill="#e8889b" /><rect x="17" y="9.3" width="2.4" height="3.6" rx=".8" fill="#f6e29a" />
    </g>
    <!-- low disk: a drive with its bar nearly full -->
    <g v-else-if="name === 'inc_disk'">
      <rect x="2.5" y="6" width="19" height="12" rx="3.4" fill="#cdd4df" />
      <rect x="5" y="10" width="11" height="4" rx="1.4" fill="#eef1f5" />
      <rect x="5" y="10" width="9.6" height="4" rx="1.4" fill="#efa274" />
      <circle cx="18.6" cy="12" r="1.3" fill="#e8889b" />
    </g>
    <!-- host down: a server with a soft red badge -->
    <g v-else-if="name === 'inc_hostdown'">
      <rect x="3" y="2.5" width="14" height="8" rx="2.4" fill="#cdd4df" />
      <rect x="3" y="12.5" width="14" height="8" rx="2.4" fill="#cdd4df" />
      <path d="M6 6.5h5M6 16.5h4" stroke="#5d6a7e" stroke-width="1.2" stroke-linecap="round" />
      <circle cx="18" cy="17" r="4.5" fill="#f5b6c2" />
      <path d="M16.4 15.4l3.2 3.2M19.6 15.4l-3.2 3.2" stroke="#b04a5f" stroke-width="1.4" stroke-linecap="round" />
    </g>
    <!-- password attack: a padlock with hits around it -->
    <g v-else-if="name === 'inc_auth'">
      <path d="M8 10.2V7.6a4 4 0 0 1 8 0v2.6" fill="none" stroke="#9ea9ba" stroke-width="1.8" />
      <rect x="5" y="10" width="14" height="11" rx="3" fill="#f6e29a" />
      <rect x="5" y="10" width="14" height="3" rx="1.5" fill="#fdf6d8" opacity=".7" />
      <circle cx="12" cy="15" r="1.5" fill="#9a7a1e" /><path d="M12 15.8v2.2" stroke="#9a7a1e" stroke-width="1.4" stroke-linecap="round" />
      <path d="M2.4 4.8l1.8 1.4M21.6 4.8l-1.8 1.4M2.4 10.6h1.6M20 10.6h1.6" stroke="#e8889b" stroke-width="1.4" stroke-linecap="round" />
    </g>
    <!-- error logs: a page of lines, the red ones climbing -->
    <g v-else-if="name === 'inc_logs'">
      <path d="M5 4A2 2 0 0 1 7 2h7.5L19 6.5V20a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2z" fill="#eef1f5" />
      <path d="M14.5 2v3a1.5 1.5 0 0 0 1.5 1.5h3z" fill="#cdd4df" />
      <path d="M8 10h3" stroke="#9ea9ba" stroke-width="1.4" stroke-linecap="round" />
      <path d="M8 13h6M8 16h8M8 19h5" stroke="#e8889b" stroke-width="1.4" stroke-linecap="round" />
    </g>
    <!-- containers: a shipping box, with what went wrong on its face -->
    <g v-else-if="name === 'inc_ctr_cpu' || name === 'inc_ctr_mem' || name === 'inc_ctr_down'">
      <path d="M12 2.8l8.5 4.7L12 12.2 3.5 7.5z" fill="#e2f3fc" />
      <path d="M3.5 7.5L12 12.2v9.3l-8.5-4.7z" fill="#acdcf3" />
      <path d="M20.5 7.5L12 12.2v9.3l8.5-4.7z" fill="#6fb6dc" />
      <g v-if="name === 'inc_ctr_cpu'"><path d="M14 18.3v-3.4l1.9-1v3.4zM16.9 16.7v-4.6l1.7-1v4.6z" fill="#f5b6c2" /></g>
      <g v-else-if="name === 'inc_ctr_mem'"><path d="M13.8 18.4v-4l5-2.7v4z" fill="#f6e29a" /></g>
      <g v-else><circle cx="16.4" cy="15" r="3.1" fill="#f5b6c2" /><rect x="15.2" y="13.8" width="2.4" height="2.4" rx=".5" fill="#fde5ea" /></g>
    </g>
    <circle v-else cx="12" cy="12" r="8" fill="#cdd4df" />
      </g>
    </defs>
    <!-- the colour, printed a touch off the line, with paper grain -->
    <use :href="`#${id}a`" transform="translate(0.7 0.8)" :filter="`url(#${id}g)`" />
    <!-- the pen: the same shapes traced by hand, thin plum, with a gap or two where the pen lifted -->
    <use :href="`#${id}a`" class="pen" :filter="`url(#${id}w)`" />
  </svg>
</template>
<style scoped>
.ui-glyph { flex: none; display: block; overflow: visible; }
.pen { fill-opacity: 0; stroke: #463a58; stroke-width: 0.95; stroke-linejoin: round; stroke-linecap: round; stroke-dasharray: 26 1.6 9 2.4 40 1.2; }
</style>
