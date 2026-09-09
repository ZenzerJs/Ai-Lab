---
task_id: MOCK-001
title: Refactor Payment Error Boundary
model: gemini-2.5-pro
target_repo: .
runs_per_arm: 3
---

# Task Prompt

Refactor error boundary in payment processing module to capture transient network failures and retry with exponential backoff.
