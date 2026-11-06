# TSK-023 — Execution ledger

Status: COMPLETE

New files use diff-only exception (a). Existing files use targeted patches. Theme styling is isolated in a stylesheet imported after the original design system, with explicit dark-theme selectors and semantic layer tokens. Existing palette is preserved.

Symbols: ThemeToggle handles persisted/system preference; ProviderIcon maps recorded model families to official marks; Shell composes theme control; Simulator and Evidence display provider identity; App tags preserved destination containers for entrance motion.

Official marks are sourced from provider-owned sites/CDNs and retained locally. Source URLs and attribution accompany assets. No external logo lookup service or runtime tracking request is added.

The user refined the first dark experiment to Obsidian Violet. Applied the exact supplied palette to canvas, chrome, cards, hero, borders, actions, and text. Replaced the Google favicon with a transparent official PNG and the OpenAI docs favicon with the official monochrome Blossom. Monochrome artwork becomes white in dark mode without changing its geometry.

Ledger cells now use a provider icon beside a stacked experiment/model label. Numeric headers and amounts align right. Verified evidence uses a mint shield and text rather than a filled green chip. Removed decorative status/navigation dots, replaced snapshot/open-source markers with meaningful icons, removed blue category accents, and made labels angular and restrained.

Motion remains CSS-based, with optional native theme crossfade. No new runtime dependencies were added. Theme crossfade permits pointer input; system reduced-motion preference disables transitions and added transforms.
