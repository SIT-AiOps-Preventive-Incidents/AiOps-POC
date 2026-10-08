import { defineStore } from "pinia";
import { api } from "@/lib/api";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Service map state shared by the canvas, the side panel and the test-request panel:
 * the graph, the selected box, the filter, and the life cycle of a test request.
 */
export const useMapStore = defineStore("map", {
  state: () => ({
    data: null,
    selected: null,
    filter: "all", // all | problems | host:<name>
    test: { phase: "idle", run: null, hops: [], error: null, step: -1 },
  }),
  actions: {
    async load(refresh = false) {
      this.data = await api.map.get(refresh);
    },
    select(id) {
      this.selected = this.selected === id ? null : id;
    },
    /** Send a real request, wait for its trace, then turn spans into ordered hops for playback. */
    async runTest() {
      this.test = { phase: "sending", run: null, hops: [], error: null, step: -1 };
      try {
        let run = await api.map.startTest();
        if (run.status === "failed") throw new Error(run.error || "request failed");
        this.test.phase = "tracing";
        this.test.run = run;
        for (let i = 0; i < 40 && run.status !== "complete"; i++) {
          await sleep(1000);
          run = await api.map.getTest(run.id);
          this.test.run = run;
        }
        this.test.hops = toHops(run.spans || []);
        if (!this.test.hops.length) throw new Error("The request finished but its trace did not arrive yet. Try again.");
        this.test.phase = "playing";
      } catch (e) {
        this.test.phase = "error";
        this.test.error = e.message;
      }
    },
    resetTest() {
      this.test = { phase: "idle", run: null, hops: [], error: null, step: -1 };
    },
  },
});

/** Spans -> hops between services, in start order, with timing relative to the first span. */
export function toHops(spans) {
  if (!spans.length) return [];
  const byId = Object.fromEntries(spans.map((s) => [s.id, s]));
  const t0 = Math.min(...spans.map((s) => s.start));
  const root = spans.find((s) => !byId[s.parent]) || spans[0];
  const hops = [{ from: "clients", to: root.service, instance: root.instance, start: 0,
    duration: root.end - root.start, error: root.error, message: root.status_msg, name: root.name }];
  for (const s of [...spans].sort((a, b) => a.start - b.start)) {
    const p = byId[s.parent];
    if (!p || p.service === s.service) continue; // internal/client spans stay inside their service
    hops.push({ from: p.service, fromInstance: p.instance, to: s.service, instance: s.instance, start: s.start - t0,
      duration: s.end - s.start, error: s.error, message: s.status_msg, name: s.name });
  }
  return hops;
}
