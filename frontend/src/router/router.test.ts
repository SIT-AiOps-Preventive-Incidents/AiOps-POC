// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import router from "./index";

describe("application routes", () => {
  it("keeps every designed and legacy workflow addressable", () => {
    const paths = router.getRoutes().map((route) => route.path);
    for (const path of [
      "/",
      "/map",
      "/services",
      "/services/:service",
      "/infra",
      "/infra/:name",
      "/problems",
      "/problems/:id(\\d+)",
      "/deployments",
      "/connect",
      "/connect/service",
      "/connect/computer",
      "/skills",
      "/runbooks",
      "/notifications",
      "/chaos",
      "/settings",
    ]) {
      expect(paths).toContain(path);
    }
  });
});
