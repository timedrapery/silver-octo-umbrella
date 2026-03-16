# Sprint 2.1 Plan

## 1. Current findings workflow assessment
- Findings are persisted and traceable to adapter runs.
- The panel supports basic type/severity/text filtering and row detail inspection.
- Severity is visually highlighted and run linkage appears in details.

## 2. Why the current findings experience still falls short
- No durable review state; analysts cannot track triage progress across sessions.
- Filtering is too narrow (missing adapter, target, review-state dimensions).
- Sorting controls are absent, reducing scan efficiency.
- Quick triage actions do not exist in the workflow.
- Case-level triage progress is not surfaced.
- Report does not reflect triage outcomes (flagged/dismissed/reviewed posture).
- Findings workflow logic is UI-bound instead of service-backed.

## 3. Sprint 2.1 scope
- Add durable finding triage model with persisted fields:
  - `review_state` (`NEW`, `REVIEWED`, `FLAGGED`, `DISMISSED`)
  - `analyst_note` (lightweight free text)
- Add safe schema migration and defaults for existing databases/findings.
- Add service-backed findings triage logic for:
  - filtering
  - sorting
  - triage summary counts
  - option derivation for filters
- Add case-service triage update methods.
- Redesign findings panel as a triage workspace:
  - summary cards
  - multi-dimension filters
  - sorting controls
  - triage action buttons
  - richer, structured detail view
- Surface case-level triage metrics in case details.
- Update report template to include triage breakdown and flagged/dismissed emphasis.
- Add tests for triage persistence, migration safety, service logic, and reporting output.

## 4. Acceptance criteria
- Findings persist review state and analyst note across reload.
- Existing databases are upgraded safely with triage defaults.
- Analysts can filter by review state, severity, adapter, target, type, and text.
- Analysts can sort by newest, oldest, severity, adapter, and target.
- Analysts can mark findings as `NEW`, `REVIEWED`, `FLAGGED`, or `DISMISSED` directly in findings panel.
- Case view and findings view show triage progress metrics.
- Report output includes triage-state breakdown and flagged finding emphasis.
- New triage behavior is covered by tests.

## 5. Risks / tradeoffs
- GUI interaction tests remain limited; logic is moved to service layer for deterministic testing.
- Triage model intentionally lightweight; no full audit trail/versioning is added in this sprint.
- Sorting/filtering are in-memory for case-local data; no SQL query engine is introduced.

## 6. Recommended next sprint
- Add analyst assignment, saved triage views, and review timeline/history for team workflows.
