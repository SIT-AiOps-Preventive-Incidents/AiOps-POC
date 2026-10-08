<script setup lang="ts">
import { computed } from "vue";
import { Line } from "vue-chartjs";
import {
  CategoryScale,
  Chart as ChartJS,
  Filler,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import type { SeriesPoint } from "@/types/api";

ChartJS.register(
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
  Filler,
);
const props = withDefaults(
  defineProps<{
    label: string;
    value: string;
    points: SeriesPoint[];
    color?: string;
  }>(),
  { color: "#1496ff" },
);
const chartData = computed(() => ({
  labels: props.points.map((point) =>
    new Date(point[0] * 1000).toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    }),
  ),
  datasets: [
    {
      data: props.points.map((point) => point[1]),
      borderColor: props.color,
      backgroundColor: `${props.color}20`,
      borderWidth: 2,
      pointRadius: 0,
      fill: true,
      tension: 0.35,
    },
  ],
}));
const options = {
  responsive: true,
  maintainAspectRatio: false,
  animation: false as const,
  plugins: { legend: { display: false } },
  scales: { x: { display: false }, y: { display: false, beginAtZero: true } },
};
</script>

<template>
  <article class="chart-card">
    <header>
      <span>{{ label }}</span
      ><strong>{{ value }}</strong>
    </header>
    <div v-if="points.length > 1" class="chart">
      <Line :data="chartData" :options="options" />
    </div>
    <div v-else class="chart empty-chart">Waiting for data</div>
  </article>
</template>
<style scoped>
.chart-card {
  height: 188px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: white;
  padding: 14px;
}
.chart-card header {
  display: flex;
  height: 24px;
  align-items: center;
  justify-content: space-between;
}
.chart-card header span {
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 500;
}
.chart-card header strong {
  font-size: 14px;
}
.chart {
  height: 126px;
  margin-top: 10px;
}
.empty-chart {
  display: grid;
  place-items: center;
  color: var(--color-text-dim);
  font-size: 12px;
}
</style>
