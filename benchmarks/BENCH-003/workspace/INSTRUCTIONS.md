# BENCH-003: Behaviour-Preserving Event Parser Refactor

## Assignment
Split the monolithic event parser in `event_parser.py` into a clean, maintainable Python package while preserving the exact public entry point, return types, exception behavior, and Unicode support.

## Structural Requirements
Refactor into an `event_parser/` package with clear separation of responsibilities:
1. `event_parser/models.py`:
   - `EventRecord`: dataclass with `event_id: str`, `event_type: str`, `version: str`, `timestamp: str`, `payload: dict`, `metadata: dict`.
2. `event_parser/validator.py`:
   - Exception classes: `ParserError` (base), `ValidationError`, `UnsupportedEventVersionError`.
   - `validate_raw_event(data: dict) -> None`: Validates required fields (`event_id`, `event_type`, `version`, `timestamp`, `payload`) and supported version (`"1.0"` or `"2.0"`).
3. `event_parser/normalizer.py`:
   - Normalization helpers: `normalize_timestamp(ts: str) -> str`, `normalize_payload(payload: dict) -> dict`. Preserves Unicode strings byte-for-byte.
4. `event_parser/__init__.py`:
   - Public exports: `parse_event`, `parse_event_stream`, `EventRecord`, `ParserError`, `ValidationError`, `UnsupportedEventVersionError`.
   - Provide backward compatibility so `from event_parser import parse_event` or `import event_parser; event_parser.parse_event(...)` works seamlessly.
5. Max Line Limit: No file in `event_parser/` should exceed 150 lines.

## Behavioral Contract
- `parse_event(raw: str | bytes | dict) -> EventRecord`
  - Parses JSON strings, bytes, or Python dicts.
  - Malformed JSON string raises `ParserError`.
  - Missing required fields raises `ValidationError`.
  - Version not in `["1.0", "2.0"]` raises `UnsupportedEventVersionError`.
- `parse_event_stream(stream: Iterable[str | bytes | dict]) -> list[EventRecord]`
  - Preserves exact input stream ordering.
- Zero mutable global state: successive calls must not share or accumulate mutable buffers.
