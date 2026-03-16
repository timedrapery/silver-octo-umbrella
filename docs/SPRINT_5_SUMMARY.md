# Sprint 5 Summary

## 1. What changed

Sprint 5 delivered a case chronology layer and reliability hardening while preserving existing architecture.

Implemented:
- new unified timeline domain service: `app/services/timeline_service.py`
- case-service timeline API: `CaseService.get_case_timeline`
- new case timeline UI tab: `app/gui/timeline_panel.py`
- case panel recent-activity view backed by timeline service
- chronology-aware HTML reporting section: Case Activity Timeline
- investigation adapter timeout boundaries for deterministic completion
- orchestrator provider timeout boundaries for deterministic partial-failure handling
- worker payload-shape consistency fix for no-adapter scenarios
- main-window triage refresh wiring bug fix

## 2. How the case timeline/history works

Timeline generation is service-driven and derived from durable records already in the case model.

Current event sources include:
- case create/update markers
- targets and notes
- saved search create/update events
- adapter run execution outcomes
- finding collection events with severity/review context
- entity research events (from entity metadata source)
- evidence promotion/addition events (including provider and reliability metadata when available)

Each timeline item includes:
- case linkage
- timestamp
- category
- event type
- concise summary
- source object references and optional metadata

Events are sorted reverse-chronologically for operational readability.

## 3. How chronology is reflected in reports

`ReportService.generate_html` now passes a bounded timeline event feed to the template.

The HTML report includes a `Case Activity Timeline` section with:
- timestamp
- category
- event type
- concise summary

This gives report readers a quick chronological narrative of how the case progressed, not only static section snapshots.

## 4. What full-suite reliability issues were addressed

Hardening changes:
- InvestigationService now enforces bounded adapter runtime via `asyncio.wait_for` and timeout-configurable failure behavior.
- MultiSourceOrchestrator now enforces bounded provider runtime and records timeout failures without aborting successful provider results.
- Worker completion payload shape is now deterministic even when no adapters are available.
- MainWindow triage refresh flow now consistently refreshes all dependent panels after triage updates.

## 5. User-facing workflow improvements

- Added dedicated Timeline tab for case activity history and drill-in details.
- Added Recent Activity section in Cases panel for immediate chronology context.
- Reports now communicate progression over time, improving handoff quality and continuity.

## 6. Service/storage/model improvements

- Added timeline domain service and event model without creating a parallel persistence subsystem.
- Exposed timeline through CaseService to keep UI/reporting consumers consistent.
- Kept timeline derivation case-native and typed, aligned with existing service/storage patterns.

## 7. Tests added or improved

Added:
- `tests/test_timeline_service.py`
  - chronology ordering
  - category/event coverage
  - case linkage and limit behavior
- orchestrator timeout test in `tests/test_intelligence_orchestrator.py`
- investigation adapter-timeout test in `tests/test_services.py`
- report chronology assertion in `tests/test_services.py`

## 8. Tradeoffs / deferred work

- Timeline currently derives from durable records and available timestamps; it is not a full immutable event-sourcing ledger.
- True historical timestamps for some state transitions (for example triage-state mutation time) remain limited by current persistence model.
- Timeline filtering is category-level today; richer pivot filters are deferred.

## 9. Remaining known stability issues, if any

- Full-suite execution in this environment can still be interrupted externally (observed KeyboardInterrupt during broader runs).
- No unresolved deterministic hang was reproduced inside hardened service paths after timeout controls were added.

## 10. Recommended Sprint 6

Sprint 6 should focus on mission intake and dashboard coherence:
- mission brief and structured objective intake
- case dashboard with workflow-stage indicators
- priority lead queue and chronology health metrics
- guided analyst workflow checklist to reduce operator overload
