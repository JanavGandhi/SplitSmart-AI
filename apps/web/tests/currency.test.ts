import { describe, expect, it } from "vitest";

import { paiseToCurrency, rupeesToPaise } from "../src/lib/currency";

describe("currency helpers", () => {
  it("formats paise as Indian rupees", () => {
    expect(paiseToCurrency(1234567)).toBe("₹12,345.67");
  });

  it("converts rupees to integer paise", () => {
    expect(rupeesToPaise(123.45)).toBe(12345);
  });
});
