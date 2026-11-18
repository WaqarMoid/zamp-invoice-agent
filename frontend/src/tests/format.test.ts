import { describe, it, expect } from "vitest";
import {
  formatMoney,
  formatCompactMoney,
  formatDate,
  formatRelativeTime,
  formatDuration,
} from "../lib/format";

describe("formatMoney", () => {
  it("formats positive numbers with INR currency grouping and two decimal places", () => {
    const formatted = formatMoney(129682.0);
    // Indian grouping: 1,29,682.00
    expect(formatted).toContain("1,29,682.00");
  });

  it("handles string representations and decimals correctly", () => {
    const formatted = formatMoney("45675.5");
    expect(formatted).toContain("45,675.50");
  });

  it("handles null or undefined safely", () => {
    expect(formatMoney(null)).toBe("—");
    expect(formatMoney(undefined)).toBe("—");
    expect(formatMoney("")).toBe("—");
  });
});

describe("formatCompactMoney", () => {
  it("formats amounts >= 1 crore with Cr suffix", () => {
    expect(formatCompactMoney(12500000)).toBe("₹1.25 Cr");
    expect(formatCompactMoney(25000000)).toBe("₹2.50 Cr");
  });

  it("formats amounts >= 1 lakh with L suffix", () => {
    expect(formatCompactMoney(1240000)).toBe("₹12.4 L");
    expect(formatCompactMoney(100000)).toBe("₹1.0 L");
  });

  it("formats amounts < 1 lakh using full INR format", () => {
    const res = formatCompactMoney(45675);
    expect(res).toContain("45,675.00");
  });
});

describe("formatDate", () => {
  it("formats ISO date string into DD MMM YYYY format", () => {
    expect(formatDate("2026-11-12")).toBe("12 Nov 2026");
    expect(formatDate("2026-04-14T10:30:00Z")).toContain("2026");
  });

  it("handles empty or null dates safely", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate(undefined)).toBe("—");
  });
});

describe("formatRelativeTime", () => {
  it("handles recent dates and boundaries", () => {
    const nowIso = new Date().toISOString();
    expect(formatRelativeTime(nowIso)).toBe("just now");

    const twoMinAgo = new Date(Date.now() - 120 * 1000).toISOString();
    expect(formatRelativeTime(twoMinAgo)).toBe("2 min ago");

    const threeHoursAgo = new Date(Date.now() - 3 * 3600 * 1000).toISOString();
    expect(formatRelativeTime(threeHoursAgo)).toBe("3 hours ago");
  });
});

describe("formatDuration", () => {
  it("formats milliseconds into seconds string with one decimal place", () => {
    expect(formatDuration(3400)).toBe("3.4 s");
    expect(formatDuration(210)).toBe("0.2 s");
    expect(formatDuration(null)).toBe("—");
  });
});
