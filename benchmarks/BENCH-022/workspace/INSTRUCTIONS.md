# BENCH-022: Multi-Window Rate Limiter and Quota Rule Chain

Repair only models.py, clock.py, windows.py, bucket.py, limiter.py, and
chain.py. Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.Decision enum: allow / deny. ConfigError on bad config.
- models.Quota(name, limit, window_seconds, kind, refill_per_second):
  validated — limit a positive int, window_seconds > 0, kind one of
  "fixed"/"sliding"/"bucket", bucket quotas carry refill_per_second > 0.
- models.Rule(pattern, action): "*" matches everything, "p:*" matches a
  prefix, otherwise exact; action coerced from string to Decision.
- clock.ManualClock: callable clock driven by .advance(seconds>0).
- windows.FixedWindow: counts per [start, start+window) bucket; an event
  exactly at a boundary belongs to the next window; count() only sees
  the current window (old buckets never inflate it).
- windows.SlidingLog: counts events strictly inside (now-window, now];
  an event exactly at the cutoff is excluded.
- bucket.TokenBucket(capacity, refill_per_second, clock): lazy refill
  computed from the injected clock, capped at capacity; try_consume(n)
  is all-or-nothing and rejects n < 1.
- limiter.RateLimiter(quotas, clock): quotas enforced PER SUBJECT; allow()
  is atomic — a denial consumes nothing on any quota; remaining(name,
  subject) reports headroom (KeyError on unknown name).
- chain.RuleChain(rules, default): DENY outranks ALLOW regardless of
  rule order; no match falls back to the validated default; explain()
  returns (decision, matching patterns).

Visible tests are smoke coverage, not the complete specification.
