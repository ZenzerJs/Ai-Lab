# TSK-024 — Publication plan

Status: APPROVED

Manifest: existing approved frontend changes in dashboard/, associated artifacts/TSK-022 and TSK-023, docs catalog/log/concept, TSK-022/023 contracts; new TSK-024 contracts. No workflow or telemetry changes planned.

| Objective | Machine-verifiable criterion | Verification |
|---|---|---|
| Clean release | TypeScript/Pages build and whitespace pass | Filtered npm build and git diff --check |
| Knowledge | Frontmatter passes | Filtered lint_frontmatter.py |
| Safe push | Remote main is an ancestor; no force update | git ls-remote, fetch, merge-base; normal git push |
| Publication | Remote main matches local commit; Pages run succeeds | GitHub Actions API and remote ref |
| Live frontend | Public HTML references new application assets; assets expose new theme/features | Public HTTP checks or browser verification |

Gate reviewed and approved under the user's explicit push instruction. Proceed to execution; no additional approval required.
