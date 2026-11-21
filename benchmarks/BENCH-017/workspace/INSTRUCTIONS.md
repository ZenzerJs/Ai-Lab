# BENCH-017: Cron Expression Parser & Timezone-Aware Schedule Evaluator

Repair only models.py, parser.py, matcher.py, and scheduler.py.
Python stdlib only (zoneinfo allowed); no network, sleeps, or paid services.

## API and invariants

- models.FieldSpec(name, minimum, maximum, names) is a frozen dataclass;
  MINUTE(0-59), HOUR(0-23), DAY(1-31), MONTH(1-12, JAN..DEC names),
  WEEKDAY(0-7, SUN..SAT names, 7 normalizes to Sunday=0).
  ALL_DAYS / ALL_WEEKDAYS cover the full normalized weekday range {0..6}.
  CronSchedule(minute, hour, day, month, weekday, raw) is a frozen dataclass
  whose fields are frozensets of ints; raw is the original expression.
- parser.parse_field(expr, spec) -> frozenset[int]. Supports "*", "a-b",
  "*/n", "a-b/n", "a/n" (atom to field maximum), and comma lists.
  Named months/weekdays are case-insensitive. Step must be a positive digit
  run; reversed ranges, out-of-range atoms, unknown names, empty parts,
  extra "/", and malformed input all raise ValueError. Weekday 7 -> 0.
- parser.parse(expr) -> CronSchedule: exactly five whitespace-separated
  fields; surrounding and repeated whitespace is fine; wrong field count or
  non-string input raises ValueError.
- matcher.cron_weekday(dt) maps datetime weekday to cron convention
  (Sunday=0 ... Saturday=6). matcher.matches(schedule, dt) requires minute,
  hour and month membership; day-of-month and weekday combine with classic
  cron OR semantics when BOTH are restricted (differ from their full range),
  and conjunctively otherwise.
- scheduler.next_runs(schedule, after, tz, count) -> list of aware datetimes
  strictly after `after` (which must be timezone-aware), ascending. `tz` is
  a zoneinfo.ZoneInfo or an IANA name string. Scanning happens over local
  wall-clock minutes in `tz`: nonexistent times (spring-forward gap) never
  match, ambiguous times (fall-back overlap) yield only their first
  (fold=0) occurrence. count < 1 raises ValueError; a schedule with no
  matching run within five years raises ValueError.
- scheduler.next_run(schedule, after, tz) is next_runs(..., 1)[0].

Visible tests are smoke coverage, not the complete specification.
