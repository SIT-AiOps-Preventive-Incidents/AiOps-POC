import { describe, expect, it } from "vitest";
import { duration, milliseconds, percent, titleCase } from "./format";

describe("format helpers", () => {
  it("formats API metric values consistently", () => {
    expect(percent(0.052)).toBe("5.2%");
    expect(milliseconds(1420)).toBe("1.42 s");
    expect(duration(125)).toBe("2m 5s");
  });

  it("turns backend statuses into readable labels", () => {
    expect(titleCase("awaiting_approval")).toBe("Awaiting Approval");
  });
});
