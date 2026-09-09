# Task Stage Contract: 05_retro

## Task Metadata
- **Task ID:** TSK-XXX
- **Title:** [Task Name]
- **Status:** ACTIVE | CLOSED
- **Prerequisite:** `04_verify.md` passed with exit code 0

---

## 1. Retrospective Overview
[High-level reflection on task execution, architectural decisions, and unexpected findings.]

---

## 2. Key Learnings & Architectural Insights
- **What went well:** [Item 1]
- **Challenges encountered:** [Item 2]
- **Patterns to standardize:** [Item 3]

---

## 3. Knowledge Propagation & Documentation Updates
*Propagate architectural findings, new schemas, and system evolutions into `docs/`.*

| Concept / Doc Updated | Path in `docs/` | Update Nature (`Creation` / `Update` / `Deprecation`) | Summary of Changes |
|---|---|---|---|
| Architecture Concept | `docs/concepts/...` | Update | Documented new subsystem interface |
| Schema Contract | `docs/schemas/...` | Creation | Added data contract schema |

---

## 4. `docs/log.md` Append Entry
*Append the following entry directly to the top of `docs/log.md` under the current date heading:*

```markdown
## YYYY-MM-DD
* **[Creation / Update / Deprecation]**: [Brief description referencing concept link](/concepts/example.md)
```

---

## 5. Final Task Closure Checklist
- [ ] Retrospective observations documented.
- [ ] Knowledge propagated to appropriate `docs/` concept documents.
- [ ] Chronological entry appended to `docs/log.md`.
- [ ] `docs/lint_frontmatter.py` re-run and confirmed clean.
- [ ] Task marked as CLOSED.
