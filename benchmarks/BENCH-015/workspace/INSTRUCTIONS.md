# BENCH-015: Signed Webhook Ingress & Idempotency Gateway

Repair only models.py, signer.py, idempotency.py, and gateway.py.
Use Python stdlib only; no network or paid services.

## API and invariants

- models defines frozen dataclasses Delivery(event_id, payload, timestamp,
  signature) and Receipt(event_id, status, digest), plus SignatureError (a
  PermissionError subclass) and ConflictError (a RuntimeError subclass).
  Delivery: event_id a nonempty str; payload bytes only; timestamp a
  nonnegative int (bool rejected); signature a nonempty str. Receipt.status
  must be "processed" or "duplicate".
- signer.Signer(secret, tolerance_seconds=300, clock=time.time): secret a
  nonempty str; tolerance a nonnegative number.
  sign(payload, timestamp) -> lowercase hex HMAC-SHA256 of the message
  b"{timestamp}.{payload}" — the timestamp IS bound into the signed message,
  so a signature minted for one timestamp fails at any other.
  verify(payload, timestamp, signature) -> bool: False for non-bytes payload,
  non-int timestamp, empty or non-str signature, or |clock() - timestamp| >
  tolerance (a delta of exactly tolerance IS within the window). The
  comparison MUST be constant-time via hmac.compare_digest.
- idempotency.IdempotencyStore(clock, ttl_seconds=None) keys deliveries by
  idempotency key. record(key, digest) returns "new" for unseen or TTL-expired
  keys (re-stamping the entry), "duplicate" when the stored digest matches,
  and "conflict" when it differs. lookup(key) returns the stored digest or
  None (expired entries are evicted). ttl_seconds must be a positive number
  when set; key and digest must be nonempty strings.
- gateway.WebhookGateway(signer, store).receive(event_id, payload, timestamp,
  signature, idempotency_key): builds a Delivery, verifies the signature FIRST
  (SignatureError on failure — nothing is recorded on a bad signature), then
  dedupes by idempotency key: conflict -> ConflictError; duplicate -> Receipt
  carrying the ORIGINAL event_id and digest with status "duplicate"; new ->
  Receipt(event_id, "processed", sha256-hex of payload), retained for future
  duplicates.

Visible tests are smoke coverage, not the complete specification.
