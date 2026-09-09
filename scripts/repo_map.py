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

    # Top-of-file module docstring detection (skips shebang, encoding comments, blank lines)
    for i, line in enumerate(tc.lines):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith(('"""', "'''", 'r"""', "r'''", 'u"""', "u'''")):
            delimiter = s[:3] if s.startswith(('"""', "'''")) else s[1:4]
            rest = s[len(delimiter):]
            lois.add(i)
            if delimiter in rest:
                break
            for j in range(i + 1, len(tc.lines)):
                lois.add(j)
                if delimiter in tc.lines[j]:
                    break
            break
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


def format_map_candidate(
    file_blocks: List[Tuple[str, str]],
    num_full_files: int,
    partial_lines: Optional[int],
    max_tokens: int,
    enc,
) -> Tuple[str, int]:
    """Format full repository map candidate with telemetry header and return (rendered_text, token_count)."""
    total_files = len(file_blocks)
    chunks = []
    included_files_count = num_full_files

    for i in range(num_full_files):
        path, content = file_blocks[i]
        chunks.append(f"### {path}\n{content}")

    prune_msg = ""
    if partial_lines is not None and num_full_files < total_files:
        path, content = file_blocks[num_full_files]
        lines = content.splitlines()
        if partial_lines > 0:
            sub = "\n".join(lines[:partial_lines])
            chunks.append(f"### {path}\n{sub}")
            included_files_count += 1
            if num_full_files > 0:
                prune_msg = (
                    f"\n\n# [Repo map pruned via binary search: {num_full_files} full files + "
                    f"first {partial_lines}/{len(lines)} lines of {path} included]"
                )
            else:
                prune_msg = (
                    f"\n\n# [Repo map pruned via binary search: "
                    f"first {partial_lines}/{len(lines)} lines included]"
                )
    elif num_full_files < total_files:
        prune_msg = (
            f"\n\n# [Repo map pruned via binary search: {num_full_files}/{total_files} files "
            f"included to enforce token budget]"
        )

    body = "\n\n".join(chunks)
    if prune_msg:
        body += prune_msg

    # Telemetry header: compute exact token count with header included in total
    header_prefix = f"# Repository Map (Symbols: {total_files} files | Tokens: "
    header_suffix = f" / {max_tokens})\n"
    candidate_tokens = count_tokens(header_prefix + f"0000{header_suffix}" + body, enc)
    candidate_header = f"# Repository Map (Symbols: {total_files} files | Tokens: {candidate_tokens} / {max_tokens})\n"
    full_output = candidate_header + body
    exact_tokens = count_tokens(full_output, enc)
    if exact_tokens != candidate_tokens:
        candidate_header = f"# Repository Map (Symbols: {total_files} files | Tokens: {exact_tokens} / {max_tokens})\n"
        full_output = candidate_header + body
        exact_tokens = count_tokens(full_output, enc)

    return full_output, exact_tokens


def binary_search_prune(file_blocks: List[Tuple[str, str]], max_tokens: int, enc) -> str:
    """
    Binary search over file blocks and lines to maximize symbol payload
    while strictly guaranteeing the total emitted output remains <= max_tokens.
    """
    total_files = len(file_blocks)
    if total_files == 0:
        return "# Repository Map: No AST symbols detected."

    # 1. Check if complete repo map fits
    full_text, tokens = format_map_candidate(file_blocks, total_files, None, max_tokens, enc)
    if tokens <= max_tokens:
        return full_text

    # 2. Binary search over number of full files [0, total_files]
    low = 0
    high = total_files
    best_full_files = 0
    best_text = ""

    while low <= high:
        mid = (low + high) // 2
        cand_text, cand_tokens = format_map_candidate(file_blocks, mid, None, max_tokens, enc)
        if cand_tokens <= max_tokens:
            best_full_files = mid
            best_text = cand_text
            low = mid + 1
        else:
            high = mid - 1

    # 3. If there is a boundary file, binary search lines of the next file
    if best_full_files < total_files:
        next_path, next_content = file_blocks[best_full_files]
        next_lines = next_content.splitlines()
        l_low = 1
        l_high = len(next_lines)
        while l_low <= l_high:
            l_mid = (l_low + l_high) // 2
            cand_text, cand_tokens = format_map_candidate(
                file_blocks, best_full_files, l_mid, max_tokens, enc
            )
            if cand_tokens <= max_tokens:
                best_text = cand_text
                l_low = l_mid + 1
            else:
                l_high = l_mid - 1

    # 4. Fallback for extremely tight budgets: ensure <= max_tokens
    if not best_text or count_tokens(best_text, enc) > max_tokens:
        minimal_header = f"# Repository Map (Symbols: {total_files} files | Tokens: {max_tokens} / {max_tokens})\n"
        best_text = minimal_header
        encoded = enc.encode(best_text)
        if len(encoded) > max_tokens:
            best_text = enc.decode(encoded[:max_tokens])

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

    # Perform binary-search pruning against max_tokens (strictly bounded)
    final_output = binary_search_prune(file_blocks, max_tokens, enc)
    print(final_output)


if __name__ == "__main__":
    main()
