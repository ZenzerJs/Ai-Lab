/**
 * Shared formatting utilities for numbers, currencies, percentages, and tokens.
 * Eliminates double-negatives (e.g. +-$0.001) and negative zero (-$0.0000).
 */

export function formatCurrency(val: number, precision?: number): string {
  if (!Number.isFinite(val) || Math.abs(val) < 0.000005) {
    return '$0.0000';
  }
  const isNegative = val < 0;
  const abs = Math.abs(val);
  const decimals = precision !== undefined ? precision : abs >= 1 ? 2 : 4;
  return `${isNegative ? '-' : ''}$${abs.toFixed(decimals)}`;
}

export function formatSignedCurrency(val: number, precision?: number): string {
  if (!Number.isFinite(val) || Math.abs(val) < 0.000005) {
    return '$0.0000';
  }
  const sign = val > 0 ? '+' : '-';
  const abs = Math.abs(val);
  const decimals = precision !== undefined ? precision : abs >= 1 ? 2 : 4;
  return `${sign}$${abs.toFixed(decimals)}`;
}

export function formatSignedPercent(val: number, precision = 1): string {
  if (!Number.isFinite(val) || Math.abs(val) < 0.05) {
    return '0.0%';
  }
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(precision)}%`;
}

export function formatTokens(val: number): string {
  if (!Number.isFinite(val)) return '0';
  return Math.round(val).toLocaleString();
}
