# Operator UI — approved UX-01/02/03 and Q-01

Design baseline: PO-approved v0.2.0. Task: SREB-11. No prototype fixture data is
embedded in the application: rows/counts/history come from actual protected APIs.

Board access key / Connect / Disconnect includes plain key-provider help and
explains the separation from Jira/GitHub and webhook credentials. The key stays
in tab memory; disconnect/reload clears it. Locked UI exposes no alert data.
Active/Resolved tabs, clickable titles, search/severity and next-step actions
implement the reviewed journeys. P1–P4 have no unapproved meaning expansion.
Resolved has no advance/reopen action; loaded-only filtering/counts and latest-500
truncation are disclosed for both scopes.

Initial loading, initial failure, loaded-data failure/staleness, empty/filter-empty,
authentication denial and version-conflict states are explicit. A conflict is not
automatically retried with a newer version. Detail results are guarded by session
and selection identity. Disconnect clears hidden retained-detail content too.
Surviving row actions keep focus during polling; removing a focused row returns
focus to the visible view heading. Dialog close returns focus to its alert when
still present, otherwise the heading; disconnected users return to the key field.
Dates include timezone. Table overflow is confined to its scroll container.

Regressions were written against the accepted behavior before correction: old
detail response overwrites the selected alert, disconnect leaves protected detail
in DOM, focused row disappearance loses focus; all three failed before the fix.
An additional first-load failure test exposed ambiguous loading/empty output and
was corrected separately. Unit tests use DOM/fetch doubles, not browser evidence.
Actual desktop/390px, keyboard, dialog, network-error and full-flow checks remain
required on the exact integrated candidate. No full WCAG conformance is claimed.

Real PR-preview browser testing exposed another gap in the DOM double: disabling
the active button blurs focus before render can preserve it. A new regression
simulates native disable/blur and failed before correction. The implementation
restores the next action or visible heading after success, unless the user moved
focus to another control. Connect/Disconnect also set deliberate focus targets.
This validates why mocked-DOM unit passes cannot replace actual browser QA.
Unknown transport/server outcomes say the update could not be confirmed, rather
than claiming no mutation occurred. Refresh is required before another attempt.
Real two-session conflict testing exposed the same disable/blur issue on rejected
updates; focus restoration therefore runs after both success and error unless
the session changed or the user selected another control. First-load failure
focuses the visible heading and suggests Refresh/Disconnect without claiming data.
The asynchronous Connect continuation also checks session identity before starting
polling or moving focus; an old response cannot create a second polling timer.
Disconnect resets filters as well as protected content before a new session.
