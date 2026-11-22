# BENCH-029: Thompson NFA Regex Engine

Repair only syntax.py, parser.py, nfa.py, compiler.py, matcher.py, and
engine.py. Python stdlib only; no network, sleeps, or paid services.

## Language and API

- parser.parse(pattern) -> AST (syntax.Char/Any/Class/Concat/Alt/Star/
  Plus/Opt). Precedence: '|' loosest, then concatenation, then postfix
  '*','+','?' binding to the PRECEDING ATOM. Groups '(...)', '.',
  '[...]' classes ('^' negation, 'a-z' ranges), and escapes \\d \\w \\s
  \\n \\t plus escaped literals. Malformed input raises ParseError.
- compiler.compile(ast) -> nfa.NFA via Thompson construction: Star
  needs both the skip edge AND the loop-back edge; Plus loops back
  without the skip.
- matcher.closure(states): TRANSITIVE epsilon closure.
  run(nfa, text, pos): sorted end offsets reaching the accept state.
- engine.Regex(pattern): match(text) -> longest anchored end or None;
  search(text) -> leftmost-LONGEST (start, end) or None; findall(text)
  -> non-overlapping leftmost-longest NON-EMPTY matched substrings.

Visible tests are smoke coverage, not the complete specification.
