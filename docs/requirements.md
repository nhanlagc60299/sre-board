# Requirements and decision proposal

Version: 0.2. SREB-1 / SREB-2. D1–D10 approved by the PO for the local pilot;
see `decisions.md`. Running-app business acceptance remains pending.

## Confirmed requirements
- REQ-01: receive pipeline alerts via webhook.
- REQ-02: show severity P1/P2/P3/P4 separately from handling state.
- REQ-03: support Acknowledge → Investigating → Monitoring → Resolved.
- REQ-04: Resolved automatically leaves the active report; not automatic data deletion.

## Approved local-pilot contract — D1–D10
D1. POST `/api/webhook` JSON: `event_id`, `title`, `pipeline`, `severity`.
All required strings; severity from sender exactly P1–P4, never inferred from state.
Lengths: event_id 1–128, title 1–200, pipeline 1–120 Unicode characters after trim.
Reject unknown fields/types, invalid severity, malformed JSON, body >16 KiB.
Create: HTTP 201 with `{alert, duplicate:false}`; validation: 400; too large: 413.
D2. New alerts start at `New`, before Acknowledge.
D3. Only the next transition is allowed: New → Acknowledge → Investigating →
Monitoring → Resolved. Reject skip/back/reopen/self transitions with 409.
D4. Dedup by event_id: exact same normalized payload returns existing alert,
HTTP 200 duplicate:true, without changing state or appending history.
Same event_id with different normalized content returns 409. A repeat after
Resolved returns the existing resolved alert; it does not reopen it.
D5. State update uses `{state,version}`; atomic optimistic concurrency; stale
version returns 409. One winner only; no partial or duplicate history entries.
D6. Separate configured secrets for webhook and operator APIs; bearer tokens.
UI operator enters a token in a password field; keep it in memory, not localStorage.
No user-account/SSO integration in pilot; shared operator token is a documented limit.
D7. SQLite retains alerts and transition history including Resolved; read history
via operator API. No delete endpoint. Long-term retention/backup policy is deferred.
D8. Active list excludes Resolved; UI polls every 2 seconds and refreshes after a
successful update. Proposed AC: resolved alert disappears within 3 seconds in the
local acceptance environment; this is an observation target, not production SLA.
D9. Bound active list to 500 latest active alerts; display truncation clearly if
more exist. Severity counts must refer to displayed rows, not an implied global total.
D10. Local pilot only, loopback binding. Production load/SLO, TLS/SSO, retention,
backup/restore and multi-host deployment remain separate rollout decisions.

## Observable acceptance examples under the approved contract
- AC-01 / REQ-01: valid P2 webhook creates exactly one New alert with the supplied
severity; invalid input cannot create data. Duplicate and conflict behavior follows D4.
- AC-02 / REQ-02: P1/New and P4/Investigating are distinguishable; advancing state
preserves severity. No low-severity alert is hidden solely because of severity.
- AC-03 / REQ-03: the full sequential path succeeds; invalid/stale updates leave
both state and history unchanged. Concurrent same-version updates have one winner.
- AC-04 / REQ-04: from a visible Monitoring alert, Resolve removes it from active
report within D8 timing while detail/history still shows its retained record.
- AC-05 / D6: missing/wrong tokens cannot read or mutate protected data.
- AC-06 / D9: empty/error/truncation cases are explicit, not silent data loss.

## Gap ownership and closure
GAP-REQ-01: CLOSED for requirements clarification. PO explicitly approved D1–D10
for the local pilot in chat on 2026-11-11; evidence recorded in `decisions.md`.
Tests and final business acceptance remain separate tracking items.
Tracking owner: Codex. Decision maker: Anh Nhân Lê (PO), technical advice by Codex.
Original deadline: before merging behavior as accepted requirements.
Closure evidence: explicit PO response and this versioned decision record.
No test pass can close this business-decision gap.

GAP-ROL-01: no independent human technical review. Known: PO delegated agent review.
Impact: correlated implementation/test/review error. Owner: Codex; decider: PO.
Mitigation: requirement-driven assertions, negative/concurrency tests, browser checks,
review checklist, and documented limitations. Closure is not an invented approval.
