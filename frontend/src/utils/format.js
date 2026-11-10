/**
 * Currency & Number Formatting Utility
 * Formats values with thousands separators (commas) when >= 1,000.
 * Examples:
 *   1000      -> "1,000.00"
 *   1099.99   -> "1,099.99"
 *   25        -> "25.00"
 */

export function formatCurrency(amount, decimals = 2) {
  const num = Number(amount);
  if (isNaN(num)) return "0.00";
  return num.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/**
 * Formats integers / counts with thousands separators (commas) when >= 1,000.
 * Examples:
 *   1000 -> "1,000"
 *   25   -> "25"
 */
export function formatNumber(val) {
  const num = Number(val);
  if (isNaN(num)) return "0";
  return num.toLocaleString("en-US");
}

