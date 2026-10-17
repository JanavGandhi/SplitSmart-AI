/**
 * Currency formatting utilities.
 * All monetary values are stored as paise (integer, 1 INR = 100 paise).
 */

/**
 * Convert paise to rupees string with 2 decimal places.
 * @example paiseToCurrency(45050) // "₹450.50"
 */
export function paiseToCurrency(
  paise: number,
  currency: string = "INR",
): string {
  const amount = paise / 100;
  const symbol = currency === "INR" ? "₹" : currency === "USD" ? "$" : currency + " ";

  return `${symbol}${amount.toLocaleString("en-IN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Convert paise to decimal rupee number.
 */
export function paiseToRupees(paise: number): number {
  return paise / 100;
}

/**
 * Convert rupees (float) to paise (integer).
 * Safe — rounds to nearest paise.
 */
export function rupeesToPaise(rupees: number): number {
  return Math.round(rupees * 100);
}

/**
 * Format paise as a compact number (e.g., 125000 -> "₹1.25K")
 */
export function paiseToCompact(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 100000) {
    return `₹${(rupees / 100000).toFixed(1)}L`;
  }
  if (rupees >= 1000) {
    return `₹${(rupees / 1000).toFixed(1)}K`;
  }
  return `₹${rupees.toFixed(2)}`;
}

/**
 * Format paise for UPI payment (2 decimal rupees string, no symbol).
 * @example formatForUPI(45050) // "450.50"
 */
export function formatForUPI(paise: number): string {
  return (paise / 100).toFixed(2);
}
