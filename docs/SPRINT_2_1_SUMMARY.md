# Sprint 2.1 Summary

## 1. What changed
- Added durable finding triage fields to the data model:
  - `review_state` (`NEW`, `REVIEWED`, `FLAGGED`, `DISMISSED`)
  - `analyst_note`
- Extended SQLite findings persistence with triage columns and safe migration defaults for existing databases.
- Added service-backed triage logic in `app/services/findings_service.py` for:
  - multi-dimension filtering
  - sorting
  - case triage summaries
  - filter option derivation
- Added case-service triage update and summary methods.
- Rebuilt findings panel into a triage workspace with:
  - summary metrics bar
  - filters by review state, severity, adapter, target, type, and text
  - sorting controls (newest, oldest, severity, adapter, target)
  - structured detail pane with provenance and triage metadata
  - quick triage actions (new/reviewed/flagged/dismissed)
  - persisted analyst note updates
- Added case-level triage signal in case details view.
- Upgraded HTML/CSV reporting to include triage outcomes and state-specific sections.

## 2. Why the findings experience is materially better
The findings surface is now an active triage console instead of a passive table. Analysts can move findings through durable states, narrow large result sets by operationally useful dimensions, prioritize by severity and freshness, and carry triage context into reports.

## 3. User-facing workflow improvements
- Faster scanability with visible severity + review state in list rows.
- Immediate triage actions without leaving the findings workspace.
- Better provenance visibility in details (adapter, run ID, target, source, timestamp).
- Better queue management via state/adapter/target/type filters and sorting options.
- Case details now show triage progress at a glance.
- Reports now distinguish flagged and dismissed outcomes.

## 4. Service/storage/model improvements
- `Finding` model now supports review lifecycle and analyst notes.
- Storage migration path ensures legacy DBs receive triage defaults.
- Case service now supports persisted triage updates and case summary metrics.
- Findings service isolates triage business logic from widget code.

## 5. Tests added or updated
- Model tests for triage defaults and enum coverage.
- Storage tests for:
  - triage round-trip persistence
  - triage update API
  - migration adding triage columns
- Service tests for:
  - case triage update validation
  - case triage summary metrics
  - findings filter/sort behavior
- Report tests updated for triage-aware output sections.

## 6. Tradeoffs / deferred work
- No multi-analyst assignment model in this sprint.
- No review history timeline/audit trail per finding yet.
- GUI interaction tests remain indirect; core logic is tested in services.

## 7. Recommended next sprint
- Add triage timeline/history and assignment primitives.
- Add saved filter presets for recurring analyst workflows.
- Add report mode selection (executive vs analyst detailed triage view).
