/**
 * Shared formatting utilities for numbers, currencies, percentages, and tokens.
 * Eliminates double-negatives (e.g. +-$0.001), negative zero (-$0.0000),
 * and prevents fake $0.0000 / 0 tokens when numbers are null, undefined, or non-finite.
 */

export function formatCurrency(val: number | null | undefined, precision?: number): string {
  if (val === null || val === undefined || typeof val !== 'number' || !Number.isFinite(val)) {
    return '—';
  }
  if (Math.abs(val) < 0.000005) {
    const dec = precision !== undefined ? precision : 4;
    return `$0.${'0'.repeat(dec)}`;
  }
  const isNegative = val < 0;
  const abs = Math.abs(val);
  const decimals = precision !== undefined ? precision : abs >= 1 ? 2 : 4;
  return `${isNegative ? '-' : ''}$${abs.toFixed(decimals)}`;
}

export function formatSignedCurrency(val: number | null | undefined, precision?: number): string {
  if (val === null || val === undefined || typeof val !== 'number' || !Number.isFinite(val)) {
    return '—';
  }
  if (Math.abs(val) < 0.000005) {
    const dec = precision !== undefined ? precision : 4;
    return `$0.${'0'.repeat(dec)}`;
  }
  const sign = val > 0 ? '+' : '-';
  const abs = Math.abs(val);
  const decimals = precision !== undefined ? precision : abs >= 1 ? 2 : 4;
  return `${sign}$${abs.toFixed(decimals)}`;
}

export function formatSignedPercent(val: number | null | undefined, precision = 1): string {
  if (val === null || val === undefined || typeof val !== 'number' || !Number.isFinite(val)) {
    return '—';
  }
  if (Math.abs(val) < 0.05) {
    return '0.0%';
  }
  const sign = val > 0 ? '+' : '';
  return `${sign}${val.toFixed(precision)}%`;
}

export function formatTokens(val: number | null | undefined): string {
  if (val === null || val === undefined || typeof val !== 'number' || !Number.isFinite(val)) {
    return '—';
  }
  return Math.round(val).toLocaleString();
}
