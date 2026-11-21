# BENCH-016: Streaming CSV/JSONL ETL Pipeline with Dead-Letter Routing

Repair only models.py, reader.py, transformer.py, and pipeline.py.
Use Python stdlib only; no network or paid services.

## API and invariants

- models defines frozen dataclasses RawRecord(line_no, data, error=None),
  DeadLetter(line_no, error, raw), Summary(total, processed, dead_lettered),
  and PipelineResult(rows, dead_letters, summary). line_no is a positive int;
  error is a str when set. Summary fields are nonnegative ints with
  total == processed + dead_lettered. PipelineResult normalizes rows and
  dead_letters to tuples, requires rows to be dicts and dead_letters to be
  DeadLetter instances, and requires summary counts to match their lengths.
- reader.iter_jsonl(stream) yields one RawRecord per nonempty line with a
  1-based line_no: parsed JSON dicts pass through as data; invalid JSON yields
  error="invalid_json" with the raw line text as data; valid non-dict JSON
  yields error="not_object". Blank/whitespace-only lines are skipped ENTIRELY.
  Malformed input never raises.
  reader.iter_csv(stream) wraps csv.DictReader over the stream; line numbers
  start at 2 (line 1 is the header) and each row yields a dict as data.
- transformer.Transformer(schema).transform(data) -> (clean, error): schema
  maps field name -> "int" | "float" | "str"; unknown kinds raise ValueError
  at construction. Missing or None required fields return
  (None, "missing_field:<name>"); failed coercion returns
  (None, "bad_type:<name>"); non-dict data returns (None, "not_mapping").
  Coercion rules — int: int or str matching -?\d+ (bool rejected);
  float: int/float/str via float() but must be finite (bool, NaN, Infinity
  rejected); str: str only. Fields absent from the schema are dropped.
- pipeline.Pipeline(transformer).run(records) consumes ANY iterable of
  RawRecord (generators included) and returns a PipelineResult. Records with
  error set, and records failing transform, append DeadLetter(line_no,
  error, record.data) preserving input order; valid records append their
  clean dict. Processing NEVER aborts on bad rows. Summary counts are exact.

Visible tests are smoke coverage, not the complete specification.
