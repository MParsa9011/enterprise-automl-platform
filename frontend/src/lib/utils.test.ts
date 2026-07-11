import { describe, expect, it } from "vitest";

import { formatBytes, formatMetric } from "@/lib/utils";

describe("formatBytes", () => {
  it("formats zero and common sizes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(1048576)).toBe("1.0 MB");
  });
});

describe("formatMetric", () => {
  it("renders an em dash for null/undefined", () => {
    expect(formatMetric(null)).toBe("—");
    expect(formatMetric(undefined)).toBe("—");
  });

  it("keeps integers integral and rounds floats to 4 dp", () => {
    expect(formatMetric(3)).toBe("3");
    expect(formatMetric(0.5)).toBe("0.5000");
  });
});
