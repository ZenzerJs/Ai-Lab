# BENCH-013: Distributed Lock & Fencing-Token Lease Manager

Repair only models.py, clock.py, lock_store.py, and coordinator.py.
Use Python stdlib only; no network, sleeps, or paid services.

## API and invariants

- models.LockRecord(resource, owner, fencing_token, acquired_at, expires_at) is a
  frozen dataclass. resource and owner must be nonempty strings; fencing_token a
  positive int (bool rejected); acquired_at and expires_at nonnegative ints with
  expires_at strictly after acquired_at. Violations raise ValueError.
- models also defines LockConflictError, StaleTokenError (ValueError subclass),
  and OwnershipError (PermissionError subclass).
- clock.Clock(source=None) wraps an injected callable, defaulting to integer
  monotonic time (int(time.monotonic())). now() returns
  the source's current instant as an int; falsy readings like 0 are valid and
  must NOT fall back to a real clock. The source is called on every now().
- lock_store.LockStore(clock) holds locks keyed by resource. Fencing tokens are
  issued from one strictly increasing store-wide counter that is NEVER reused or
  reset, even after release, expiry reclamation, or on another resource.
  acquire(resource, owner, ttl) requires a positive int ttl. While a live lock
  exists it raises LockConflictError (even for the same owner); once no live
  lock exists it grants a LockRecord stamped with the next fencing token and
  [now, now + ttl). A lock is live iff expires_at > clock.now().
  renew(resource, owner, token, ttl) requires the same live-lookup checks plus a
  positive ttl: wrong owner raises OwnershipError, wrong token raises
  StaleTokenError, absent or expired lease raises KeyError. Token staleness
  is checked before ownership. Renewal keeps the
  SAME fencing token and acquired_at, extending expires_at to now + ttl.
  release(resource, owner, token) runs the same lookup checks and deletes the
  lock only on an exact owner AND token match.
  owner(resource) returns the live owner or None.
- coordinator.LockCoordinator(store).hold(resource, owner, ttl) is a context
  manager yielding the granted LockRecord. On exit it releases ONLY the exact
  lease it holds: if the lease expired or changed hands, the release must leave
  the current lock untouched (never delete another owner's lock). An exception
  inside the with-block still releases the lease. A lock that vanished
  underneath (KeyError) is ignored; ownership or token mismatches are also
  swallowed — the coordinator never raises them from release.

Visible tests are smoke coverage, not the complete specification.
