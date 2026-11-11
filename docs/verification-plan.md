# Verification plan and evidence ledger

Version 0.1. Expected results derive from confirmed scope plus explicitly proposed
D1–D10. Passing proposal-based tests is not proof of PO acceptance.

## Risk / requirement → test → oracle
| ID | Risk / requirement | Test | Independent expected / source | Scope |
|---|---|---|---|---|
| R1 | Hidden unresolved P1 / REQ-02,04 | mixed state/severity report | explicit fixture IDs, REQ-02/04 | integration/E2E |
| R2 | Duplicate alerts / REQ-01 | exact repeat/conflict/post-resolve | D4, fixed expected count/history | unit/integration |
| R3 | Lost update / REQ-03 | two requests at version 1 | D5 one success/one conflict | integration |
| R4 | Bad state paths / REQ-03 | all forward/invalid pairs | D3 independently enumerated pairs | unit |
| R5 | Unauthenticated changes | missing/wrong/correct token | D6 401/no mutation | HTTP integration |
| R6 | API passes, UI still visible | actual browser resolves alert | AC-04/D8 absent row, retained detail | E2E |
| R7 | Restart loses data/history | reopen SQLite store | D7 same IDs/states/history | integration |
| R8 | Injection/oversized input | script title, invalid JSON/body | text rendered inert; D1 rejects input | integration/E2E |
| R9 | Silent report truncation | >500 active records | D9 explicit truncation/count scope | integration |

## Detailed testcase: R6 / AC-04
Setup: isolated real Python HTTP server and SQLite database, actual browser; no API mocks.
Seed A Monitoring/P1, B Resolved/P2, C Investigating/P4 through actual endpoints.
Steps: enter operator token; observe A/C visible and B absent; resolve A in UI;
wait up to proposed 3 seconds; assert A absent and C still present; fetch A detail.
Expected: detail still Resolved with preserved severity and complete history.
Oracle: AC-04/D7/D8, explicit IDs; do not compute expected IDs with the production filter.
Reset: stop test server and remove disposable test database; no production fixtures.
Limits: local pilot/shared token only; browser/runtime/version recorded in run report.
Status: not implemented/not run at this revision.

## Execution requirements
Record command, start/end time, exit status, exact source SHA, environment,
Python/browser versions, dataset/reset, actual versus mocked dependencies,
pass/fail/blocked/skipped/not-run counts, logs/screenshots and known limitations.
Local results, CI runs, integrated candidate checks, PO acceptance, and post-deploy
checks are different evidence scopes. A command that did not run is not pass.

## Initial ledger
- Repository seed: actual, documentation only; no product checks applicable.
- Requirements proposal: written, PO decisions pending.
- Product tests, browser screenshots, CI: not run.
- Technical review: not performed yet.
- PO business acceptance: pending.
- External production deployment/post-deploy: not performed.

## PR and release approach
Start with charter/contract/test plan, then persistence/domain, HTTP/API, UI, and
integrated evidence/corrections. These are project-specific slices, not a mandated
handbook sequence. Each PR includes tests appropriate to its behavior and <=500
added+deleted text lines. Record dependent PR base/head and review each revision.
No deployed baseline exists: initial delivery manifest must say first local pilot,
not invent a production B. Source base is the README seed; it is not runtime B.
Build a local archive from an exact candidate and record digest. Reconcile all
changed files/commits to PRs, resolution changes, gaps, and real test evidence.
