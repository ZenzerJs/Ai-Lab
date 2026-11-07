"""Markdown AST & Wikilink Parser."""
import re
from typing import Dict, List, Tuple


class MarkdownParser:
    """Parses markdown text to extract YAML frontmatter and wikilinks."""

    WIKILINK_RE = re.compile(r"\[\[([a-zA-Z0-9_\-\s]+?)(?:#([a-zA-Z0-9_\-\s]+))?\]\]")

    def parse_wikilinks(self, content: str) -> List[Tuple[str, str]]:
        """Extract tuples of (target_page, anchor)."""
        results: List[Tuple[str, str]] = []
        for match in self.WIKILINK_RE.finditer(content):
            target = match.group(1).strip()
            anchor = match.group(2).strip() if match.group(2) else ""
            results.append((target, anchor))
        return results

    def extract_frontmatter(self, text: str) -> Dict[str, str]:
        """Extract basic key-value pairs from --- frontmatter."""
        meta: Dict[str, str] = {}
        if text.startswith("---"):
            parts = text.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        meta[k.strip()] = v.strip()
        return meta
