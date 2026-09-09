#!/usr/bin/env python3
"""
scripts/lint_frontmatter.py - OKF v0.2 Frontmatter and Integrity Validator

House Rule Rationale:
---------------------
Note: In the upstream Open Knowledge Format (OKF v0.2) base specification,
producers are permitted to include arbitrary producer-defined custom frontmatter
keys (§4.1). In this workspace, rejecting unknown frontmatter keys is an intentional
internal "house rule" designed to enforce strict schema discipline, prevent metadata
sprawl, and maintain deterministic prompt assembly across autonomous agent sessions.

Validation Rules:
1. Strict lowercase reserved filenames (index.md, log.md); reject uppercase variants (e.g., INDEX.md, LOG.md).
2. Asserts docs/index.md contains ONLY the `okf_version` frontmatter key.
3. Asserts all other non-reserved docs/**/*.md contain the required `type` field and
   conform to valid v0.2 keys (title, description, status, verified, sources, stale_after).
4. Asserts all bundle-relative links (/path/to/file.md) resolve to existing files within docs/.
5. Exits with 0 on full compliance, or 1 if any violations are found.
"""

import os
import re
import sys
import yaml
from pathlib import Path

# Ensure UTF-8 output encoding on all platforms including Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ALLOWED_CONTENT_KEYS = {
    "type",
    "title",
    "description",
    "status",
    "verified",
    "sources",
    "stale_after",
}

RESERVED_LOWERCASE = {"index.md", "log.md"}


def parse_frontmatter(content: str):
    """Extract and parse YAML frontmatter if present."""
    if not content.startswith("---"):
        return None, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content
    fm_text = parts[1]
    body = parts[2]
    try:
        data = yaml.safe_load(fm_text) or {}
        return data, body
    except yaml.YAMLError as exc:
        raise ValueError(f"Malformed YAML frontmatter: {exc}")


def check_casing_and_reserved(docs_dir: Path, errors: list):
    """Assert reserved files use strict lowercase filenames."""
    for root, dirs, files in os.walk(docs_dir):
        for fname in files:
            lower = fname.lower()
            if lower in RESERVED_LOWERCASE and fname != lower:
                rel_path = Path(root, fname).relative_to(docs_dir.parent)
                errors.append(
                    f"Casing Error: Reserved file '{rel_path}' must be strictly lowercase '{lower}'"
                )


def check_bundle_links(file_path: Path, body: str, docs_dir: Path, errors: list):
    """Find and validate bundle-relative markdown links (/path/to/target.md)."""
    # Match markdown links: [text](target) or [text](target "title")
    pattern = re.compile(r'\[([^\]]+)\]\(([^\)\s]+)(?:\s+"[^"]*")?\)')
    rel_source = file_path.relative_to(docs_dir.parent)

    for match in pattern.finditer(body):
        raw_target = match.group(2)
        # Strip anchor fragment
        link_target = raw_target.split("#")[0]
        if not link_target or link_target.startswith(("#", "http://", "https://", "mailto:")):
            continue

        if not link_target.startswith("/"):
            errors.append(
                f"Link Format Error in '{rel_source}': link '{raw_target}' must be bundle-relative starting with '/' (e.g. '/{link_target}')"
            )
            continue

        relative_target = link_target.lstrip("/")
        target_path = docs_dir / relative_target
        if not target_path.exists():
            errors.append(
                f"Broken Link in '{rel_source}': bundle-relative link '{raw_target}' does not exist on disk"
            )
        else:
            # Case sensitivity assertion across Windows and POSIX
            resolved_real = target_path.resolve().as_posix()
            expected_real = (docs_dir.resolve() / relative_target).as_posix()
            if resolved_real != expected_real:
                errors.append(
                    f"Casing Error in '{rel_source}': link '{raw_target}' casing does not match disk file casing"
                )


def lint_docs(docs_dir: Path) -> list:
    """Run all OKF v0.2 validation rules against docs directory."""
    errors = []

    if not docs_dir.exists() or not docs_dir.is_dir():
        return [f"Directory not found: {docs_dir}"]

    # 1. Casing checks
    check_casing_and_reserved(docs_dir, errors)

    root_index = docs_dir / "index.md"
    if not root_index.exists():
        errors.append("Missing bundle root index: docs/index.md must exist")

    # 2. Iterate all markdown files
    for md_file in sorted(docs_dir.rglob("*.md")):
        rel_to_docs = md_file.relative_to(docs_dir)
        rel_str = str(rel_to_docs).replace("\\", "/")

        try:
            content = md_file.read_text(encoding="utf-8-sig")
        except Exception as exc:
            errors.append(f"File Read Error in '{rel_str}': {exc}")
            continue

        try:
            fm, body = parse_frontmatter(content)
        except ValueError as exc:
            errors.append(f"Schema Violation in '{rel_str}': {exc}")
            continue

        # Bundle Root index.md rule
        if md_file.name.lower() == "index.md" and md_file.parent == docs_dir:
            if fm is None:
                errors.append(
                    f"Schema Violation in '{rel_str}': docs/index.md must have frontmatter"
                )
            else:
                fm_keys = set(fm.keys())
                if fm_keys != {"okf_version"}:
                    errors.append(
                        f"Schema Violation in '{rel_str}': docs/index.md frontmatter must contain *only* 'okf_version'. Found: {sorted(fm_keys)}"
                    )
                elif fm.get("okf_version") != "0.2":
                    errors.append(
                        f"Schema Violation in '{rel_str}': okf_version must be '0.2', got {fm.get('okf_version')!r}"
                    )

        # Reserved log.md rule
        elif md_file.name.lower() == "log.md":
            # OKF v0.2 log.md contains no frontmatter
            if fm is not None:
                errors.append(
                    f"Schema Violation in '{rel_str}': reserved log.md must not contain frontmatter"
                )

        # Content documents
        else:
            if fm is None:
                errors.append(
                    f"Schema Violation in '{rel_str}': Missing required YAML frontmatter"
                )
                continue

            # Rule: required 'type' field
            if "type" not in fm or not fm["type"]:
                errors.append(
                    f"Schema Violation in '{rel_str}': Missing required 'type' field in frontmatter"
                )

            # Rule: unknown keys forbidden (house rule)
            unknown_keys = set(fm.keys()) - ALLOWED_CONTENT_KEYS
            if unknown_keys:
                errors.append(
                    f"Schema Violation in '{rel_str}': Disallowed frontmatter keys {sorted(unknown_keys)}. Allowed keys: {sorted(ALLOWED_CONTENT_KEYS)}"
                )

        # Link integrity check
        check_bundle_links(md_file, body, docs_dir, errors)

    return errors


def main():
    workspace_root = Path(__file__).resolve().parent.parent
    docs_dir = workspace_root / "docs"

    if len(sys.argv) > 1:
        docs_dir = Path(sys.argv[1]).resolve()

    errors = lint_docs(docs_dir)

    if errors:
        sys.stderr.write(f"✗ OKF Frontmatter Lint Failed with {len(errors)} error(s):\n")
        for err in errors:
            sys.stderr.write(f"  - {err}\n")
        sys.exit(1)
    else:
        print("✓ OKF v0.2 Frontmatter Lint Passed: All docs comply with schema rules, casing, and link integrity.")
        sys.exit(0)


if __name__ == "__main__":
    main()
