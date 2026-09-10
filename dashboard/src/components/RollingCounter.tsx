import React from 'react';
import { useAnimatedCounter } from '../hooks/useAnimatedCounter';

interface RollingCounterProps {
  target: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  duration?: number;
  /** Changing this value replays the count-up sweep. */
  replayKey?: string | number;
  className?: string;
}

export const RollingCounter: React.FC<RollingCounterProps> = ({
  target,
  decimals = 4,
  prefix = '',
  suffix = '',
  duration,
  replayKey,
  className = '',
}) => {
  const ref = useAnimatedCounter({
    target,
    decimals,
    prefix,
    suffix,
    duration,
    replayKey,
  });

  return (
    <span
      ref={ref}
      className={`tabular-nums ${className}`}
      aria-label={`${prefix}${target.toFixed(decimals)}${suffix}`}
    >
      {prefix}
      {target.toFixed(decimals)}
      {suffix}
    </span>
  );
};
