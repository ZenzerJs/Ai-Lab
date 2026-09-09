# Operational Rule: Context Isolation & Targeted Symbol Querying

## Core Mandate
Agents must NEVER dump or read entire source files into context when looking up function signatures, class interfaces, or symbol locations. Direct complete-file reads are prohibited when structural lookup utilities suffice.

## Query Tools
1. **Structural AST Queries (`ast-grep`):**
   - Use `ast-grep` (`sg`) to find definitions, call sites, or pattern matches without ingesting irrelevant lines.
   - Example: `ast-grep --pattern 'def process($$$): $$$' src/`
2. **Repository Mapping (`scripts/repo_map.py`):**
   - Run `python scripts/repo_map.py --target <path>` to extract precise class outlines, signatures, and docstrings bounded within the 1,800-token margin target.
3. **Targeted Line Range Views:**
   - When inspecting implementation details, read only the specific slice identified by AST search (e.g., lines 45–75).
4. **Context Budget Protection:**
   - Reading files >100 lines without prior structural localization is treated as a token leakage violation.
