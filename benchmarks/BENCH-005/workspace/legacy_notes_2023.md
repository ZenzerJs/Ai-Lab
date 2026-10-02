# ARCHITECTURE NOTES (DEPRECATED: 2023-04-12)

**WARNING: THIS NOTE IS SUPERSEDED AND RETAINED FOR HISTORICAL AUDIT ONLY.**

In legacy design discussions, team members proposed that:
1. `config.json` should always override environment variables so deployment teams could pin configuration via disk files.
2. If an environment variable conflicts with a file key, the file key must take precedence.

DO NOT USE THIS LOGIC FOR NEW FEATURES OR TASKS. REFER TO AUTHORITATIVE CONTRACT IN INSTRUCTIONS.MD.
