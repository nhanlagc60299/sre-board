# Delivery workflow — approved v0.2 baseline

Feature/fix -> develop -> exact-SHA integrated QA -> PO candidate acceptance ->
baseline-to-final reconciliation/go-no-go -> final release PR -> main/runtime verify.

G0: requirement/oracle and applicable design decisions known. G1: author reads full
diff, records scope/dependencies/base/head/count and actual tests/evidence.
G2: latest-head checks and actual reviews complete; all feedback dispositioned.
G3: real integrated candidate tested in isolated source/config/database.
G4: explicit PO AC response on that candidate. G5: two-way release reconciliation,
policy/go-no-go/rollback. G6: verify resulting main content and actual runtime.

On failure return to corrective work through G0–G3; relevant changes invalidate
affected acceptance/evidence. Main baseline remains stable while develop changes.
No force-push/history rewrite. Main local address convention 8765; QA 8766.

## Pre-merge review gate
1. Capture full base/head, changed files and additions+deletions across text files.
2. Read every page of issue comments, inline threads and review submissions.
3. Verify asynchronous reviewers completed on this head; missing/tier-limited
   review is a gap, not an approval. Automated completion is not no-findings.
4. Fix or explicitly disposition every finding with SHA/tests/re-review. Resolve
   threads only after evidence supports the result.
5. Check new comments/checks and unchanged head/target immediately before merge.

The same Codex agent implements/tests/reviews; bots supplement this and do not
create independent human approval. Connected-account identity is transport only.

## Repository enforcement and exceptions
Remote inspection on 2026-11-12: main/develop protected=false. Protection capability
and configuration must be verified separately; this record does not claim setup.
Until verified, Codex owns this explicit manual gate and records it per PR.
Missing required evidence blocks merge even if GitHub offers a Merge button.

Current CI blocks >500 changed text lines per implementation PR. Binary screenshots
need visual review. Aggregate release has no automatic exception; present actual
count/scope for authorized policy treatment before merging an oversized release.

## Jira and cleanup
Map actual statuses: planned / In Progress / Verifying / Done. Verifying must list
which review, QA or PO gate remains; merged does not mean Done. Failed QA or PO
feedback reopens affected work. No status or sprint event is invented.
Preserve historical tests/screenshots/comments and approved submission. Archive
superseded drafts, make current docs authoritative and retain their provenance.
