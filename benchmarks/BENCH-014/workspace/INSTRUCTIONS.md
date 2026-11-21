# BENCH-014: Structured Query Filter AST & Safe SQL Compiler

Repair only ast_nodes.py, parser.py, validator.py, and compiler.py.
Use Python stdlib only; no network or paid services.

## API and invariants

- ast_nodes defines frozen dataclasses Field(name), Literal(value),
  Comparison(field, op, literal), And(children), Or(children), and Not(child).
  Field names must match `[a-zA-Z_][a-zA-Z0-9_]*`. Literals are str, int, or
  finite float only (bool and NaN/Infinity rejected). Ops are `=`, `!=`, `<`,
  `<=`, `>`, `>=`, `like`: `like` requires a string literal; ordering ops
  require numeric literals. And/Or children become a nonempty tuple of nodes;
  Not wraps exactly one node. All violations raise ValueError.
- parser.parse(text) builds the AST. Grammar: comparisons joined by AND/OR,
  parentheses, and NOT. Precedence is NOT > AND > OR: `a = 1 OR b = 2 AND c = 3`
  parses as `Or(a=1, And(b=2, c=3))`. Keywords AND/OR/NOT are uppercase only;
  `like` is a lowercase operator keyword (all are reserved words, never field
  names). Literals are single-quoted strings (backslash escapes the next char)
  or numbers (`-?\d+` -> int, `-?\d+\.\d+` -> float). `=` is equality (`==` is
  invalid). Trailing tokens, incomplete comparisons, unbalanced parens, bad
  literals, and stray characters raise ValueError.
- validator.Validator(allowed_fields).validate(node) checks EVERY Field in the
  tree at any depth against the allowlist, raising ValueError naming the
  unknown field; returns the node on success.
- compiler.SQLCompiler(allowed_fields).compile(node) returns `(sql, params)`:
  validates first, then emits `?` placeholders. Field names are emitted raw
  (safe: identifier-validated and allowlisted). EVERY literal goes into params
  in depth-first order and is NEVER interpolated into the SQL text, so hostile
  literal text cannot alter the query. `like` emits `LIKE`. And/Or wrap their
  children in parens; Not emits `NOT (...)`.

Visible tests are smoke coverage, not the complete specification.
