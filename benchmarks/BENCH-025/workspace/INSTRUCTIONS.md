# BENCH-025: Recursive-Descent Expression Language

Repair only models.py, lexer.py, parser.py, env.py, and eval.py.
Python stdlib only; no network, sleeps, or paid services.

## Grammar and invariants

- Grammar: `stmt (';' stmt)* ';'?` where a stmt is `name = expr` or an
  expression; `expr` is `term (('+'|'-') term)*`, `term` is
  `factor (('*'|'/') factor)*`, `factor` is unary +/-, atoms are
  numbers, names, or parenthesized expressions.
- lexer.tokenize: Token(kind, text, 0-based pos); unknown characters
  raise LexError naming the offset — never skipped.
- parser.Parser: strict precedence; trailing garbage is a ParseError;
  a lone trailing ';' after the last statement is allowed.
- env.Environment: parent-chain lookup; child scopes never write to a
  parent; undefined names raise EvalError.
- eval.evaluate/run: integer arithmetic; '/' requires exact division and
  nonzero divisor (EvalError otherwise); unary '-'/+';' assignments
  return the bound value; run() returns one value per statement.

Visible tests are smoke coverage, not the complete specification.
