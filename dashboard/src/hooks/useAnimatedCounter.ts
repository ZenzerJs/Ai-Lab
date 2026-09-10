import { useEffect, useRef } from 'react';

interface UseAnimatedCounterOptions {
  /** Final numeric value. */
  target: number;
  /** Fractional digits for formatting. */
  decimals?: number;
  /** Static prefix, e.g. '$' or 'n = '. */
  prefix?: string;
  /** Static suffix, e.g. '%' or ' Runs'. */
  suffix?: string;
  /** Duration in ms (ignored when user prefers reduced motion). */
  duration?: number;
  /** Re-run the sweep whenever this key changes (e.g. selected model). */
  replayKey?: string | number;
}

const easeOutExpo = (x: number): number => (x === 1 ? 1 : 1 - Math.pow(2, -10 * x));

/**
 * Animates text content of the returned ref from 0 to `target` using a single
 * requestAnimationFrame loop that writes `textContent` directly — no per-frame
 * React re-renders, no layout thrash. Respects prefers-reduced-motion by
 * rendering the final value instantly.
 */
export function useAnimatedCounter({
  target,
  decimals = 4,
  prefix = '',
  suffix = '',
  duration = 550,
  replayKey,
}: UseAnimatedCounterOptions): React.RefObject<HTMLSpanElement> {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduceMotion =
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const fmt = (v: number): string =>
      `${prefix}${v.toFixed(decimals)}${suffix}`;

    if (reduceMotion || duration <= 0) {
      el.textContent = fmt(target);
      return;
    }

    let raf = 0;
    const start = performance.now();

    const frame = (now: number): void => {
      const progress = Math.min((now - start) / duration, 1);
      el.textContent = fmt(target * easeOutExpo(progress));
      if (progress < 1) {
        raf = requestAnimationFrame(frame);
      }
    };

    el.textContent = fmt(0);
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, decimals, prefix, suffix, duration, replayKey]);

  return ref;
}
