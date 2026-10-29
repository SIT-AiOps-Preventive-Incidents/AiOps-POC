<script setup>
// Hand-drawn colour glyphs for the places that name a thing (navigation, connect choices, card titles).
// Drawn on a 24 grid like a sticker: a flat coloured body, an ink outline, one small detail in a second colour.
// No gradients, no glow. Colours are fixed mid-tones that read on both the dark and the light theme; the ink
// follows the text colour. Plain UI controls (close, chevrons, search) keep the single-colour UiIcon.
defineProps({ name: { type: String, required: true }, size: { type: Number, default: 22 } });
</script>
<template>
  <svg class="ui-glyph" :width="size" :height="size" viewBox="0 0 24 24" aria-hidden="true">
    <!-- overview: a little dashboard, two tiles and a gauge -->
    <g v-if="name === 'home'">
      <rect x="2.5" y="3.5" width="19" height="17" rx="3.5" fill="#3d7fb8" />
      <rect x="5" y="6" width="6" height="5" rx="1.3" fill="#a9d4f2" />
      <rect x="5" y="13" width="6" height="5" rx="1.3" fill="#a9d4f2" />
      <path d="M13.5 15.5a3.5 3.5 0 1 1 7 0" fill="none" stroke="#ffd36b" stroke-width="1.8" stroke-linecap="round" />
      <path d="M17 15.5l1.6-2" stroke="#fff" stroke-width="1.5" stroke-linecap="round" />
      <rect x="2.5" y="3.5" width="19" height="17" rx="3.5" fill="none" class="ink" />
    </g>
    <!-- incidents: a warning sign with a crack of light -->
    <g v-else-if="name === 'warning'">
      <path d="M10.3 3.9a2 2 0 0 1 3.4 0l8.1 13.9A2 2 0 0 1 20.1 21H3.9a2 2 0 0 1-1.7-3.2z" fill="#f1a63a" />
      <path d="M12 8.5v5.2" stroke="#3a2306" stroke-width="2" stroke-linecap="round" />
      <circle cx="12" cy="17" r="1.25" fill="#3a2306" />
      <path d="M10.3 3.9a2 2 0 0 1 3.4 0l8.1 13.9A2 2 0 0 1 20.1 21H3.9a2 2 0 0 1-1.7-3.2z" fill="none" class="ink" />
    </g>
    <!-- fleet: a rack with two blinking units -->
    <g v-else-if="name === 'server'">
      <rect x="4" y="2.5" width="16" height="8.5" rx="2.2" fill="#5b6b86" />
      <rect x="4" y="13" width="16" height="8.5" rx="2.2" fill="#5b6b86" />
      <path d="M7 6.75h6M7 17.25h6" stroke="#c9d3e3" stroke-width="1.5" stroke-linecap="round" />
      <circle cx="16.5" cy="6.75" r="1.3" fill="#4fd69c" />
      <circle cx="16.5" cy="17.25" r="1.3" fill="#ffd36b" />
      <rect x="4" y="2.5" width="16" height="8.5" rx="2.2" fill="none" class="ink" />
      <rect x="4" y="13" width="16" height="8.5" rx="2.2" fill="none" class="ink" />
    </g>
    <!-- service map: three nodes joined -->
    <g v-else-if="name === 'flowchart'">
      <path d="M7 7.5l10 3.5M7 7.5l3 9.5M17 11l-7 6" stroke="#8a93a3" stroke-width="1.5" />
      <circle cx="6.5" cy="7" r="3.5" fill="#5ab0e2" />
      <circle cx="17.5" cy="11" r="3.5" fill="#4fd69c" />
      <circle cx="10" cy="18" r="3.5" fill="#f1a63a" />
      <circle cx="6.5" cy="7" r="3.5" fill="none" class="ink" /><circle cx="17.5" cy="11" r="3.5" fill="none" class="ink" /><circle cx="10" cy="18" r="3.5" fill="none" class="ink" />
    </g>
    <!-- services: an open box -->
    <g v-else-if="name === 'cube'">
      <path d="M12 2.8l8.5 4.6v9.2L12 21.2l-8.5-4.6V7.4z" fill="#7b6fd0" />
      <path d="M3.5 7.4L12 12l8.5-4.6L12 2.8z" fill="#b3aaf0" />
      <path d="M12 12v9.2" class="ink" />
      <path d="M12 2.8l8.5 4.6v9.2L12 21.2l-8.5-4.6V7.4zM3.5 7.4L12 12l8.5-4.6" fill="none" class="ink" />
    </g>
    <!-- runbooks: a book with a bookmark -->
    <g v-else-if="name === 'book'">
      <path d="M4 4.5A2 2 0 0 1 6 2.5h13.5v16H6a2 2 0 0 0-2 2z" fill="#2f9e74" />
      <path d="M4 20.5a2 2 0 0 1 2-2h13.5v3H6a2 2 0 0 1-2-1z" fill="#d6f0e4" />
      <path d="M13 2.5v7l2-1.5 2 1.5v-7" fill="#ffd36b" />
      <path d="M4 4.5A2 2 0 0 1 6 2.5h13.5v19H6a2 2 0 0 1-2-2z" fill="none" class="ink" />
    </g>
    <!-- AI skills: a spark over a chip -->
    <g v-else-if="name === 'sparkle'">
      <rect x="4" y="9" width="12" height="12" rx="3" fill="#5ab0e2" />
      <path d="M7 13h6M7 17h4" stroke="#e7f4fc" stroke-width="1.5" stroke-linecap="round" />
      <path d="M18 2.5l1.2 3 3 1.2-3 1.2-1.2 3-1.2-3-3-1.2 3-1.2z" fill="#ffd36b" />
      <rect x="4" y="9" width="12" height="12" rx="3" fill="none" class="ink" />
      <path d="M18 2.5l1.2 3 3 1.2-3 1.2-1.2 3-1.2-3-3-1.2 3-1.2z" fill="none" class="ink" />
    </g>
    <!-- connect: a plug -->
    <g v-else-if="name === 'plug'">
      <path d="M8.5 2.5v5M15.5 2.5v5" stroke="#8a93a3" stroke-width="2" stroke-linecap="round" />
      <path d="M5.5 7.5h13v3.5a6.5 6.5 0 0 1-13 0z" fill="#4fd69c" />
      <path d="M12 17.5v4" stroke="#4fd69c" stroke-width="2.4" stroke-linecap="round" />
      <path d="M10 11.5h4" stroke="#0e3b28" stroke-width="1.5" stroke-linecap="round" />
      <path d="M5.5 7.5h13v3.5a6.5 6.5 0 0 1-13 0z" fill="none" class="ink" />
    </g>
    <!-- notifications: a bell with a red dot -->
    <g v-else-if="name === 'alert'">
      <path d="M12 3a6 6 0 0 0-6 6v4l-1.8 3.2h15.6L18 13V9a6 6 0 0 0-6-6z" fill="#f1a63a" />
      <path d="M9.5 18.5a2.5 2.5 0 0 0 5 0" fill="#c9771a" />
      <circle cx="18" cy="5" r="3" fill="#f2545b" />
      <path d="M12 3a6 6 0 0 0-6 6v4l-1.8 3.2h15.6L18 13V9a6 6 0 0 0-6-6z" fill="none" class="ink" />
    </g>
    <!-- settings: a gear -->
    <g v-else-if="name === 'settings'">
      <path d="M10.3 2.5h3.4l.5 2.4 1.9.8 2-1.4 2.4 2.4-1.4 2 .8 1.9 2.4.5v3.4l-2.4.5-.8 1.9 1.4 2-2.4 2.4-2-1.4-1.9.8-.5 2.4h-3.4l-.5-2.4-1.9-.8-2 1.4-2.4-2.4 1.4-2-.8-1.9-2.4-.5v-3.4l2.4-.5.8-1.9-1.4-2 2.4-2.4 2 1.4 1.9-.8z" fill="#8a93a3" />
      <circle cx="12" cy="12" r="3.3" fill="#e9edf3" />
      <path d="M10.3 2.5h3.4l.5 2.4 1.9.8 2-1.4 2.4 2.4-1.4 2 .8 1.9 2.4.5v3.4l-2.4.5-.8 1.9 1.4 2-2.4 2.4-2-1.4-1.9.8-.5 2.4h-3.4l-.5-2.4-1.9-.8-2 1.4-2.4-2.4 1.4-2-.8-1.9-2.4-.5v-3.4l2.4-.5.8-1.9-1.4-2 2.4-2.4 2 1.4 1.9-.8z" fill="none" class="ink" />
      <circle cx="12" cy="12" r="3.3" fill="none" class="ink" />
    </g>
    <!-- cloud: a cloud with a server window -->
    <g v-else-if="name === 'cloud'">
      <path d="M7 19.5h10.5a4.5 4.5 0 0 0 .8-8.9 6.3 6.3 0 0 0-12.1-1.4A5.2 5.2 0 0 0 7 19.5z" fill="#5ab0e2" />
      <rect x="8.5" y="12" width="7" height="4.5" rx="1" fill="#e7f4fc" />
      <circle cx="10.2" cy="14.25" r=".9" fill="#2fcf8e" />
      <path d="M7 19.5h10.5a4.5 4.5 0 0 0 .8-8.9 6.3 6.3 0 0 0-12.1-1.4A5.2 5.2 0 0 0 7 19.5z" fill="none" class="ink" />
    </g>
    <!-- demo: a lightning bolt -->
    <g v-else-if="name === 'flash'">
      <path d="M13.5 2.5L5 13.5h6l-1.5 8 8.5-11h-6z" fill="#ffd36b" />
      <path d="M13.5 2.5L5 13.5h6l-1.5 8 8.5-11h-6z" fill="none" class="ink" />
    </g>
    <!-- pricing: a tag -->
    <g v-else-if="name === 'tag'">
      <path d="M2.5 11.3V4a1.5 1.5 0 0 1 1.5-1.5h7.3l10.2 10.2-8.8 8.8z" fill="#e66aa0" />
      <circle cx="7.5" cy="7.5" r="1.8" fill="#fde6f0" />
      <path d="M2.5 11.3V4a1.5 1.5 0 0 1 1.5-1.5h7.3l10.2 10.2-8.8 8.8z" fill="none" class="ink" />
    </g>
    <!-- design system: a palette -->
    <g v-else-if="name === 'color'">
      <path d="M12 2.5a9.5 9.5 0 0 0 0 19c1.4 0 2-.9 2-1.8 0-1.6-1.5-1.7-1.5-3.2 0-1 .8-1.5 1.8-1.5h2.2A5 5 0 0 0 21.5 10C21.5 5.8 17.3 2.5 12 2.5z" fill="#e9dcc4" />
      <circle cx="7.5" cy="11" r="1.6" fill="#f2545b" /><circle cx="9.5" cy="6.8" r="1.6" fill="#ffd36b" />
      <circle cx="14.5" cy="6.5" r="1.6" fill="#4fd69c" /><circle cx="17.5" cy="10" r="1.6" fill="#5ab0e2" />
      <path d="M12 2.5a9.5 9.5 0 0 0 0 19c1.4 0 2-.9 2-1.8 0-1.6-1.5-1.7-1.5-3.2 0-1 .8-1.5 1.8-1.5h2.2A5 5 0 0 0 21.5 10C21.5 5.8 17.3 2.5 12 2.5z" fill="none" class="ink" />
    </g>
    <!-- a computer / laptop -->
    <g v-else-if="name === 'laptop'">
      <rect x="4" y="4.5" width="16" height="11" rx="2" fill="#5b6b86" />
      <rect x="6" y="6.5" width="12" height="7" rx="1" fill="#a9d4f2" />
      <path d="M2 18.5h20l-1.2 1.8a1.5 1.5 0 0 1-1.3.7H4.5a1.5 1.5 0 0 1-1.3-.7z" fill="#8a93a3" />
      <rect x="4" y="4.5" width="16" height="11" rx="2" fill="none" class="ink" /><path d="M2 18.5h20l-1.2 1.8a1.5 1.5 0 0 1-1.3.7H4.5a1.5 1.5 0 0 1-1.3-.7z" fill="none" class="ink" />
    </g>
    <!-- a website: a globe in a browser -->
    <g v-else-if="name === 'globe'">
      <circle cx="12" cy="12" r="9.5" fill="#2fa37d" />
      <path d="M6 7.5c2 .5 2.5 2 1.5 3.5s.5 3 2.5 3 1.5 3-.5 4.5M14 3c-.5 2 .5 3 2 3.5s2 2.5 1 4 .5 3 3 2.5" fill="none" stroke="#bff0dc" stroke-width="1.6" stroke-linecap="round" />
      <circle cx="12" cy="12" r="9.5" fill="none" class="ink" />
    </g>
    <!-- an app traced with OpenTelemetry: a pulse line in a window -->
    <g v-else-if="name === 'pulse'">
      <rect x="2.5" y="4" width="19" height="16" rx="3" fill="#7b6fd0" />
      <path d="M5 13h3l2-4 3 7 2-3h4" fill="none" stroke="#ffd36b" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <rect x="2.5" y="4" width="19" height="16" rx="3" fill="none" class="ink" />
    </g>
    <!-- a fix: a wrench -->
    <g v-else-if="name === 'wrench'">
      <path d="M14.5 3a5 5 0 0 0-4.7 6.7L3.6 15.9a2.1 2.1 0 0 0 3 3l6.2-6.2A5 5 0 0 0 19.5 8l-3 3-2.9-.5-.5-2.9 3-3a5 5 0 0 0-1.6-.6z" fill="#8a93a3" />
      <circle cx="5.2" cy="17.5" r="1" fill="#e9edf3" />
      <path d="M14.5 3a5 5 0 0 0-4.7 6.7L3.6 15.9a2.1 2.1 0 0 0 3 3l6.2-6.2A5 5 0 0 0 19.5 8l-3 3-2.9-.5-.5-2.9 3-3a5 5 0 0 0-1.6-.6z" fill="none" class="ink" />
    </g>
    <!-- ===== resources ===== -->
    <!-- gateway / router: a puck with four arrows -->
    <g v-else-if="name === 'router'">
      <ellipse cx="12" cy="15" rx="9.5" ry="4.5" fill="#2a6f9e" />
      <ellipse cx="12" cy="12.5" rx="9.5" ry="4.5" fill="#56b6ea" />
      <path d="M12 10.3v-3M12 7.3l-1.3 1.3M12 7.3l1.3 1.3M8.5 12.5h-3M5.5 12.5l1.3-1.1M15.5 12.5h3M18.5 12.5l-1.3-1.1" stroke="#0b2233" stroke-width="1.3" stroke-linecap="round" />
      <ellipse cx="12" cy="12.5" rx="9.5" ry="4.5" fill="none" class="ink" /><path d="M2.5 12.5V15M21.5 12.5V15" class="ink" />
    </g>
    <!-- a virtual machine: a window stacked on a host -->
    <g v-else-if="name === 'vm'">
      <rect x="2.5" y="14.5" width="19" height="6" rx="2" fill="#5b6b86" />
      <circle cx="18" cy="17.5" r="1" fill="#4fd69c" />
      <rect x="5" y="3" width="14" height="10" rx="2" fill="#f08a3c" />
      <path d="M5 6.2h14" stroke="#7a3a0c" stroke-width="1.1" />
      <path d="M8.5 9.5h4" stroke="#fff3e6" stroke-width="1.4" stroke-linecap="round" />
      <rect x="5" y="3" width="14" height="10" rx="2" fill="none" class="ink" /><rect x="2.5" y="14.5" width="19" height="6" rx="2" fill="none" class="ink" />
    </g>
    <!-- a service: stacked blocks, an app made of parts -->
    <g v-else-if="name === 'service'">
      <rect x="3" y="12.5" width="8" height="8" rx="2" fill="#56b6ea" />
      <rect x="13" y="12.5" width="8" height="8" rx="2" fill="#7b6fd0" />
      <rect x="8" y="3.5" width="8" height="8" rx="2" fill="#2fc98b" />
      <rect x="3" y="12.5" width="8" height="8" rx="2" fill="none" class="ink" /><rect x="13" y="12.5" width="8" height="8" rx="2" fill="none" class="ink" />
      <rect x="8" y="3.5" width="8" height="8" rx="2" fill="none" class="ink" />
    </g>
    <!-- a device we cannot name: a small box with a status light -->
    <g v-else-if="name === 'device'">
      <rect x="3" y="6.5" width="18" height="11" rx="2.5" fill="#6b7280" />
      <path d="M6 10.5h7M6 13.5h4" stroke="#d6dae1" stroke-width="1.4" stroke-linecap="round" />
      <circle cx="17" cy="12" r="1.5" fill="#f1a63a" />
      <rect x="3" y="6.5" width="18" height="11" rx="2.5" fill="none" class="ink" />
    </g>
    <!-- a process found running on a machine: a gear on a window -->
    <g v-else-if="name === 'process'">
      <rect x="2.5" y="4" width="19" height="16" rx="3" fill="#3f4a5e" />
      <circle cx="12" cy="12.5" r="4" fill="#ffd36b" /><circle cx="12" cy="12.5" r="1.6" fill="#3f4a5e" />
      <path d="M12 6.8v1.6M12 16.6v1.6M6.3 12.5h1.6M16.1 12.5h1.6" stroke="#ffd36b" stroke-width="1.6" stroke-linecap="round" />
      <rect x="2.5" y="4" width="19" height="16" rx="3" fill="none" class="ink" />
    </g>
    <!-- ===== incident kinds ===== -->
    <!-- failure rate: a chart line that breaks and drops into red -->
    <g v-else-if="name === 'inc_error'">
      <rect x="2.5" y="3.5" width="19" height="17" rx="3.5" fill="#2a2d35" />
      <path d="M5 15l3.5-3.5 3 2 3.5-5" fill="none" stroke="#56b6ea" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M15.5 8.5l3.5 8" fill="none" stroke="#f2545b" stroke-width="1.8" stroke-linecap="round" stroke-dasharray="1.6 2" />
      <circle cx="19" cy="16.5" r="2.2" fill="#f2545b" />
      <rect x="2.5" y="3.5" width="19" height="17" rx="3.5" fill="none" class="ink" />
    </g>
    <!-- slow responses: a stopwatch past the red mark -->
    <g v-else-if="name === 'inc_latency'">
      <rect x="10" y="1.5" width="4" height="2.5" rx="1" fill="#8a93a3" />
      <circle cx="12" cy="13" r="8.5" fill="#f1a63a" />
      <path d="M12 13V7.5A5.5 5.5 0 0 1 17.2 11" fill="#f2545b" />
      <circle cx="12" cy="13" r="5.5" fill="none" stroke="#fff3dc" stroke-width="1" opacity=".6" />
      <path d="M12 13l3.5-3" stroke="#3a2306" stroke-width="1.8" stroke-linecap="round" />
      <circle cx="12" cy="13" r="8.5" fill="none" class="ink" />
    </g>
    <!-- CPU: a chip running hot -->
    <g v-else-if="name === 'inc_cpu'">
      <path d="M8 2.5v3M12 2.5v3M16 2.5v3M8 18.5v3M12 18.5v3M16 18.5v3M2.5 8h3M2.5 12h3M2.5 16h3M18.5 8h3M18.5 12h3M18.5 16h3" stroke="#a7afbd" stroke-width="1.5" stroke-linecap="round" />
      <rect x="5" y="5" width="14" height="14" rx="2.5" fill="#3f4a5e" />
      <rect x="8.5" y="8.5" width="7" height="7" rx="1.2" fill="#f2545b" />
      <path d="M10.5 13.5c0-1.4 1.5-1.6 1.5-3 .9.6 1.5 1.6 1.5 2.4a1.5 1.5 0 0 1-3 .6z" fill="#ffd36b" />
      <rect x="5" y="5" width="14" height="14" rx="2.5" fill="none" class="ink" />
    </g>
    <!-- memory: a RAM stick, its cells filled up -->
    <g v-else-if="name === 'inc_mem'">
      <path d="M2.5 8.5a1.5 1.5 0 0 1 1.5-1.5h16a1.5 1.5 0 0 1 1.5 1.5V15H2.5z" fill="#2f9e74" />
      <path d="M4 15v2.5M7 15v2.5M10 15v2.5M14 15v2.5M17 15v2.5M20 15v2.5" stroke="#ffd36b" stroke-width="1.4" stroke-linecap="round" />
      <rect x="5" y="9" width="3" height="4" rx=".6" fill="#f2545b" /><rect x="9" y="9" width="3" height="4" rx=".6" fill="#f2545b" />
      <rect x="13" y="9" width="3" height="4" rx=".6" fill="#f2545b" /><rect x="17" y="9" width="2.5" height="4" rx=".6" fill="#f1a63a" />
      <path d="M2.5 8.5a1.5 1.5 0 0 1 1.5-1.5h16a1.5 1.5 0 0 1 1.5 1.5V15H2.5z" fill="none" class="ink" />
    </g>
    <!-- low disk: a drive with its bar nearly full -->
    <g v-else-if="name === 'inc_disk'">
      <rect x="2.5" y="6" width="19" height="12" rx="3" fill="#5b6b86" />
      <rect x="5" y="10" width="11" height="4" rx="1.2" fill="#2a2d35" />
      <rect x="5" y="10" width="10" height="4" rx="1.2" fill="#f1a63a" />
      <circle cx="18.5" cy="12" r="1.3" fill="#f2545b" />
      <rect x="2.5" y="6" width="19" height="12" rx="3" fill="none" class="ink" />
    </g>
    <!-- host down: a server with a red cross -->
    <g v-else-if="name === 'inc_hostdown'">
      <rect x="3.5" y="2.5" width="14" height="8" rx="2" fill="#5b6b86" />
      <rect x="3.5" y="12.5" width="14" height="8" rx="2" fill="#5b6b86" />
      <path d="M6.5 6.5h5M6.5 16.5h5" stroke="#c9d3e3" stroke-width="1.4" stroke-linecap="round" />
      <circle cx="18" cy="17" r="4.5" fill="#f2545b" />
      <path d="M16.3 15.3l3.4 3.4M19.7 15.3l-3.4 3.4" stroke="#fff" stroke-width="1.6" stroke-linecap="round" />
      <rect x="3.5" y="2.5" width="14" height="8" rx="2" fill="none" class="ink" /><circle cx="18" cy="17" r="4.5" fill="none" class="ink" />
    </g>
    <!-- password attack: a padlock with hits around it -->
    <g v-else-if="name === 'inc_auth'">
      <path d="M8 10V7.5a4 4 0 0 1 8 0V10" fill="none" stroke="#a7afbd" stroke-width="2" />
      <rect x="5" y="10" width="14" height="11" rx="2.5" fill="#f1a63a" />
      <circle cx="12" cy="14.6" r="1.6" fill="#3a2306" /><path d="M12 15.5v2.5" stroke="#3a2306" stroke-width="1.6" stroke-linecap="round" />
      <path d="M2 4.5l2 1.5M22 4.5l-2 1.5M2.5 10.5h1.5M20 10.5h1.5" stroke="#f2545b" stroke-width="1.6" stroke-linecap="round" />
      <rect x="5" y="10" width="14" height="11" rx="2.5" fill="none" class="ink" />
    </g>
    <!-- error logs: a page of lines, red ones climbing -->
    <g v-else-if="name === 'inc_logs'">
      <path d="M5 3.5A1.5 1.5 0 0 1 6.5 2h8l4.5 4.5v14A1.5 1.5 0 0 1 17.5 22h-11A1.5 1.5 0 0 1 5 20.5z" fill="#e9edf3" />
      <path d="M14.5 2v4.5H19" fill="#c9d3e3" />
      <path d="M8 10h8M8 13h6M8 16h8M8 19h5" stroke-width="1.6" stroke-linecap="round" stroke="#f2545b" />
      <path d="M8 10h3" stroke="#8a93a3" stroke-width="1.6" stroke-linecap="round" />
      <path d="M5 3.5A1.5 1.5 0 0 1 6.5 2h8l4.5 4.5v14A1.5 1.5 0 0 1 17.5 22h-11A1.5 1.5 0 0 1 5 20.5z" fill="none" class="ink" />
    </g>
    <!-- containers: a shipping box, with what went wrong on its face -->
    <g v-else-if="name === 'inc_ctr_cpu' || name === 'inc_ctr_mem' || name === 'inc_ctr_down'">
      <path d="M12 2.8l8.5 4.6v9.2L12 21.2l-8.5-4.6V7.4z" fill="#3d7fb8" />
      <path d="M3.5 7.4L12 12l8.5-4.6L12 2.8z" fill="#7fb6e3" />
      <path d="M12 12v9.2" class="ink" />
      <g v-if="name === 'inc_ctr_cpu'"><path d="M14 18.2v-3.4l2 -1.1v3.4zM17 16.6v-4.6l1.8-1v4.6z" fill="#f2545b" /></g>
      <g v-else-if="name === 'inc_ctr_mem'"><path d="M13.8 18.4v-4l5-2.7v4z" fill="#f1a63a" /><path d="M15.3 17.6v-3M17.3 16.5v-3" stroke="#3a2306" stroke-width=".9" /></g>
      <g v-else><circle cx="16.4" cy="15" r="3.3" fill="#f2545b" /><rect x="15.1" y="13.7" width="2.6" height="2.6" rx=".4" fill="#fff" /></g>
      <path d="M12 2.8l8.5 4.6v9.2L12 21.2l-8.5-4.6V7.4zM3.5 7.4L12 12l8.5-4.6" fill="none" class="ink" />
    </g>
    <circle v-else cx="12" cy="12" r="8" fill="#8a93a3" />
  </svg>
</template>
<style scoped>
.ui-glyph { flex: none; display: block; }
/* the outline every glyph shares: the text colour, so it sits right on both themes */
.ink { stroke: var(--c-glyph-ink, #0b0c0e); stroke-width: 1.3; stroke-linejoin: round; stroke-linecap: round; }
</style>
