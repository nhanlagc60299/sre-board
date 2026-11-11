# Decision record — local pilot v0.1

Date: 2026-11-11, Asia/Ho_Chi_Minh. PO: Anh Nhan Le (`nhanlagc60299`).
Source: explicit user replies in the Codex project chat, not inferred from commits.

## Confirmed decisions
1. The user is PO and business decision maker.
2. Codex handles implementation, testing, and technical review. This is technical
self-review by the same coding agent, not an independent human approval.
3. Build the SRE Board case from the handbook.
4. PO explicitly approved D1–D10 in `requirements.md` v0.1 for a local pilot.
5. All project documentation, Jira items, code, UI, screenshots and evidence are English.

D1–D10 are now the approved pilot contract, not unconfirmed implementation guesses.
The original proposal remains versioned in PR #1; this record establishes approval.
It does not establish PO acceptance of the completed application.

## Technical findings and corrections
- Initial restricted test execution could not bind loopback: environment blocked.
The actual HTTP suite then ran successfully with loopback permission.
- SREB-6: late responses after disconnect/reconnect and focus loss on polling.
Three regression tests failed before correction, then passed. A fourth test exposed
a stale 401 response disconnecting a newer session; it failed before its correction.
All four regression tests then passed.
These are unit tests with mocked DOM/fetch; browser evidence remains separate.
- A retained-history ID lookup lets the PO inspect an alert after its row disappears.
This is an interface for D7's retained detail, not a change in retention policy.
- main is the actual source integration branch. No master/UAT/production deployment
exists; the first local pilot must not invent a deployed baseline B.

## Remaining decisions/evidence
PO business acceptance: pending a real demonstration and explicit response.
Independent human review: absent, disclosed; not fabricated or required by delegation.
Public production rollout, SSO/TLS, long-term retention, backups and load SLOs:
not part of this local pilot and not implicitly approved.
