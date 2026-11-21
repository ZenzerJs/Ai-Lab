# BENCH-009: Multi-File Token-Bucket Rate Limiter

Repair only models.py, bucket.py, registry.py, and middleware.py.
Use Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.as_decimal(value) converts Decimal, integer, string, or float via
  Decimal(str(value)); reject booleans, non-finite or negative values with ValueError.
- models.BucketState(capacity, refill_rate, tokens, updated_at) is a dataclass.
  Normalize all fields to Decimal; capacity must be positive, tokens <= capacity.
  updated_at must be nonnegative. refill_rate may be zero.
- bucket.TokenBucket(capacity, refill_rate, clock=time.monotonic) starts full,
  timestamped by the injected callable. Expose its state as .state.
  refill(now=None) uses the injected clock when omitted; add elapsed * refill_rate
  exactly and cap at capacity, retaining fractional tokens without float arithmetic.
  Ignore backward time entirely (do not lower updated_at).
  consume(amount=1, now=None) refills and consumes the entire positive amount if
  available, returning True; otherwise return False without deducting tokens.
  Invalid amounts raise ValueError before any mutation.
- registry.BucketRegistry(clock=time.monotonic) owns independent buckets indexed
  by (tenant_id, bucket_name).
  add(tenant_id, name, capacity, refill_rate) creates and returns a TokenBucket;
  duplicate keys raise ValueError without replacement.
  get(tenant_id, name) returns it, or raises KeyError. No shared mutable defaults
  between tenants, names, or registry instances.
- middleware.RateLimiter(registry).consume(tenant_id, requests) accepts an iterable
  of (bucket_name, amount) pairs, including repeated bucket names and generators.
  Empty requests return True. Validate all positive amounts and resolve every
  bucket before mutation; invalid amounts raise ValueError, missing keys KeyError.
  Sample the registry clock once per nonempty request and refill every participating
  bucket at that same instant. Aggregate repeated names. Return True only when
  every bucket can pay its whole requested amount.
  On False or any exception, restore ALL participating tokens AND updated_at to
  their exact pre-request values, including refills. On success deduct all amounts.
  Atomic means all-or-nothing state changes within one call; thread safety is not
  required. Never affect a different tenant.

Visible tests are smoke coverage, not the complete specification.
