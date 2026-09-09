#!/usr/bin/env python3
"""
scripts/repo_map.py - Structural AST Repository Mapper with Binary-Search Token Pruning

Features:
- Traverses repository tree or specific target files.
- Uses `grep-ast` TreeContext and tree-sitter AST parsing to extract:
  - Class definitions
  - Function / method signatures and type annotations
  - Docstrings
- Uses `tiktoken` (cl100k_base) to measure token budget.
- Tokenizer Margin Rule: Enforces a strict internal target of 1,800 tokens
  (accounting for OpenAI BPE vs. Gemini tokenizer variance, guaranteeing <= 2,000 in Antigravity).
- Employs binary search pruning when extracted symbols exceed the budget.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import tiktoken
from grep_ast import TreeContext, filename_to_lang

# Ensure UTF-8 output encoding on all platforms including Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DEFAULT_TARGET_TOKENS = 1800
ENCODING_NAME = "cl100k_base"

IGNORE_DIRS = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    ".system_generated",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "egg-info",
}

DEF_NODE_TYPES = {
    # Python
    "class_definition",
    "function_definition",
    "decorated_definition",
    # JavaScript / TypeScript
    "class_declaration",
    "function_declaration",
    "method_definition",
    "interface_declaration",
    "type_alias_declaration",
    "export_statement",
    # Go
    "function_declaration",
    "method_declaration",
    "type_declaration",
    # Rust
    "function_item",
    "struct_item",
    "enum_item",
    "trait_item",
    "impl_item",
    # Java / C / C++
    "class_declaration",
    "method_declaration",
    "field_declaration",
}


def count_tokens(text: str, enc) -> int:
    """Calculate token count using tiktoken."""
    return len(enc.encode(text))


def extract_symbols_from_file(file_path: Path) -> Optional[str]:
    """
    Extract class definitions, function signatures, and docstrings from a single file
    using grep-ast TreeContext.
    """
    try:
        code = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None

    if not code.strip():
        return None

    # Check if grep-ast supports this file
    lang = filename_to_lang(str(file_path))
    if not lang:
        return None

    try:
        tc = TreeContext(
            filename=str(file_path),
            code=code,
            color=False,
            line_number=True,
            mark_lois=False,
            margin=0,
            parent_context=False,
            child_context=False,
            last_line=False,
            loi_pad=0,
        )
    except Exception:
        return None

    lois: Set[int] = set()

    # Traverse AST nodes
    for line_idx, nodes in enumerate(tc.nodes):
        for node in nodes:
            if node.type in DEF_NODE_TYPES:
                block_start = None
                for child in node.children:
                    if child.type in ("block", "statement_block", "body", "declaration_list"):
                        block_start = child.start_point[0]
                        # Capture docstrings
                        for sub in child.children:
                            if sub.type == "string" or (
                                sub.type == "expression_statement"
                                and any(e.type == "string" for e in sub.children)
                            ):
                                for doc_l in range(sub.start_point[0], sub.end_point[0] + 1):
                                    lois.add(doc_l)
                            # Only check the first statement in the block for docstring
                            break
                        break

                sig_end = block_start if block_start is not None else node.end_point[0]
                for sig_l in range(node.start_point[0], sig_end):
                    lois.add(sig_l)

    # Top-of-file module docstring detection
    if tc.lines and tc.lines[0].strip().startswith(('"""', "'''")):
        in_doc = True
        for i, l in enumerate(tc.lines):
            lois.add(i)
            if i > 0 and ('"""' in l or "'''" in l):
                break

    # Fallback to regex if AST didn't capture symbols
    if not lois:
        import re
        patterns = [
            re.compile(r"^\s*(?:async\s+)?def\s+[a-zA-Z_]"),
            re.compile(r"^\s*class\s+[a-zA-Z_]"),
            re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:class|interface|type|function)\s+[a-zA-Z_]"),
        ]
        for idx, line in enumerate(tc.lines):
            if any(p.search(line) for p in patterns):
                lois.add(idx)

    if not lois:
        return None

    tc.add_lines_of_interest(lois)
    tc.add_context()
    formatted = tc.format()
    return formatted.strip()


def collect_target_files(target_path: Path, root_path: Path) -> List[Path]:
    """Collect all source files matching the target criteria."""
    collected = []
    if target_path.is_file():
        return [target_path]

    if not target_path.exists():
        return []

    for root, dirs, files in os.walk(target_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in sorted(files):
            fp = Path(root, f)
            if filename_to_lang(str(fp)):
                collected.append(fp)

    return collected


def render_map(file_blocks: List[Tuple[str, str]], prune_ratio: float = 1.0) -> str:
    """
    Render repo map given a list of (relative_path, symbol_content) tuples
    and an inclusion pruning ratio [0.0, 1.0].
    """
    total_blocks = len(file_blocks)
    if total_blocks == 0:
        return ""

    num_to_include = max(1, int(round(total_blocks * prune_ratio)))
    included_blocks = file_blocks[:num_to_include]

    chunks = []
    for rel_path, content in included_blocks:
        chunks.append(f"### {rel_path}\n{content}")

    rendered = "\n\n".join(chunks)
    if num_to_include < total_blocks:
        rendered += (
            f"\n\n# [Repo map pruned via binary search: {num_to_include}/{total_blocks} files "
            f"included to enforce token budget]"
        )
    return rendered


def binary_search_prune(file_blocks: List[Tuple[str, str]], max_tokens: int, enc) -> str:
    """
    Binary search over inclusion ratios to find the maximum symbol payload
    that fits strictly within max_tokens.
    """
    full_text = render_map(file_blocks, prune_ratio=1.0)
    if count_tokens(full_text, enc) <= max_tokens:
        return full_text

    low = 1
    high = len(file_blocks)
    best_text = ""

    while low <= high:
        mid = (low + high) // 2
        ratio = mid / len(file_blocks)
        candidate = render_map(file_blocks, prune_ratio=ratio)
        tokens = count_tokens(candidate, enc)

        if tokens <= max_tokens:
            best_text = candidate
            low = mid + 1  # Try including more
        else:
            high = mid - 1  # Reduce inclusion

    if not best_text and file_blocks:
        # Edge case: Even 1 file exceeds max_tokens. Binary search lines of first file.
        first_path, first_content = file_blocks[0]
        lines = first_content.splitlines()
        l_low, l_high = 1, len(lines)
        best_lines = ""
        while l_low <= l_high:
            l_mid = (l_low + l_high) // 2
            sub_content = "\n".join(lines[:l_mid])
            candidate = (
                f"### {first_path}\n{sub_content}\n\n# [Repo map pruned via binary search: "
                f"first {l_mid}/{len(lines)} lines included]"
            )
            if count_tokens(candidate, enc) <= max_tokens:
                best_lines = candidate
                l_low = l_mid + 1
            else:
                l_high = l_mid - 1
        return best_lines or candidate[:500]

    return best_text


def main():
    parser = argparse.ArgumentParser(
        description="Extract structural AST repository symbol map with tiktoken budget pruning."
    )
    parser.add_argument(
        "--target",
        type=str,
        default=None,
        help="Target file or directory to map (defaults to repository root).",
    )
    parser.add_argument(
        "--root",
        type=str,
        default=".",
        help="Root directory of the workspace (default: current directory).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_TARGET_TOKENS,
        help=f"Maximum allowed tokens (Tokenizer Margin Rule target, default: {DEFAULT_TARGET_TOKENS}).",
    )
    args = parser.parse_args()

    workspace_root = Path(args.root).resolve()
    target_path = Path(args.target).resolve() if args.target else workspace_root
    max_tokens = args.max_tokens

    enc = tiktoken.get_encoding(ENCODING_NAME)

    files = collect_target_files(target_path, workspace_root)
    if not files:
        sys.stderr.write(f"No parseable source files found in target: {target_path}\n")
        sys.exit(0)

    file_blocks: List[Tuple[str, str]] = []
    for fp in files:
        symbols = extract_symbols_from_file(fp)
        if symbols:
            try:
                rel_path = fp.relative_to(workspace_root)
            except ValueError:
                rel_path = fp
            file_blocks.append((str(rel_path).replace("\\", "/"), symbols))

    if not file_blocks:
        print("# Repository Map: No AST symbols detected.")
        sys.exit(0)

    # Perform binary-search pruning against max_tokens
    final_map = binary_search_prune(file_blocks, max_tokens, enc)
    token_count = count_tokens(final_map, enc)

    # Header with token telemetry
    print(f"# Repository Map (Symbols: {len(file_blocks)} files | Tokens: {token_count} / {max_tokens})")
    print(final_map)


if __name__ == "__main__":
    main()
