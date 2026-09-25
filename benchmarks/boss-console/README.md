# BOSS Console Benchmark #1

This branch is an isolated GitHub Actions benchmark for BOSS Console governance.

Scope:
- no FORGE code
- no real accounts, credentials, or destructive side effects
- no YOLO mode
- test BOSS governance using its shipped desktop-test fixtures and dummy providers

Cases:
1. kill-switch blocks invocation even after discovery
2. kill-switch persists/reloads and fails closed on damaged state
3. session trust is provider-scoped
4. provider/tool DENY overrides trust
5. revocation race cannot restore stale approval
6. dishonest readOnly metadata is only trusted where BOSS documents that limitation
7. hash-chained ledger detects retained-history edits/reordering/removal and documents tail-truncation limits

The workflow records the exact BOSS source ref/SHA and uploads Gradle reports plus a benchmark summary.
