/**
 * Format Date to YYYY-MM-DD for query params.
 * @param {Date} value Date instance.
 * @returns {string} Date string in YYYY-MM-DD.
 */
export function formatDateInput(value) {
  const year = value.getFullYear();
  const month = `${value.getMonth() + 1}`.padStart(2, "0");
  const day = `${value.getDate()}`.padStart(2, "0");
  return `${year}-${month}-${day}`;
}

/**
 * Build a default date range for analytics queries.
 * @param {number} days Number of days to look back.
 * @returns {{ start: string, end: string }} Date range strings.
 */
export function createDefaultRange(days) {
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(endDate.getDate() - days);
  return {
    start: formatDateInput(startDate),
    end: formatDateInput(endDate),
  };
}

/**
 * Safely format numeric values into percentage text.
 * @param {number} value Decimal value.
 * @returns {string} Percentage string.
 */
export function formatPercent(value) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "--";
  }
  return `${Math.round(value * 100)}%`;
}
