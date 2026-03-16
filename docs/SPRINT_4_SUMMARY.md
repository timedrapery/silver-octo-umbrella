# Sprint 4 Summary - Entity Research and Evidence Promotion

## Outcome

Sprint 4 delivered a case-native entity research workflow that connects orchestration output to analyst review and durable evidence promotion, without introducing parallel schemas or disconnected subsystems.

## What Was Implemented

### 1. Entity research service workflow

Implemented `app/services/entity_research_service.py` as the Sprint 4 orchestration-to-promotion backbone.

Delivered capabilities:
- typed research session model for analyst review surfaces
- entity upsert behavior bound to existing case entities
- normalized review items with key fields, provenance, and reliability hints
- promotion flow that writes durable evidence using the existing repository
- deterministic fingerprint deduplication to prevent duplicate promotions

### 2. Case continuity support

Extended `app/services/case_service.py` with entity/evidence continuity APIs:
- `list_entities(case_id)`
- `list_evidence(case_id)`
- `get_case_entity_activity_summary(case_id)`

Added `EntityActivitySummary` for panel/report continuity metrics.

### 3. Entity research analyst workspace

Added new panel `app/gui/entity_research_panel.py` and integrated it as a first-class tab.

Delivered UX elements:
- entity request input with auto/type-specific execution
- provider execution summary table (success, duration, result count, error)
- structured review queue with per-item selection and promotion status
- promotion controls with reliability level and analyst notes
- status feedback and case refresh propagation after promotion

### 4. Main window integration

Updated `app/gui/main_window.py` to:
- initialize intelligence repository and multi-source orchestrator via `EntityResearchService`
- register the Entity Research tab in primary navigation
- propagate active case changes to the research panel
- refresh research panel and case detail after investigation and triage updates

### 5. Case panel continuity signals

Updated `app/gui/case_panel.py` to surface Sprint 4 continuity information:
- researched entities / research evidence / last research timestamp
- promoted evidence preview list in case details

### 6. Reporting uplift

Updated `app/reports/templates/report.html.j2` with Sprint 4 reporting sections:
- Entity Research Workspace Activity
- Promoted Research Evidence

This keeps promoted orchestration evidence visible in analyst-facing exports.

### 7. Test coverage

Extended `tests/test_services.py` with Sprint 4 checks:
- case entity activity summary behavior
- entity research session + promotion deduplication behavior
- report output assertions for new Sprint 4 sections

## Engineering Notes

- Reused existing `MultiSourceOrchestrator`, `ManagedNetworkClient`, and `IntelligenceRepository`.
- Preserved existing typed models and persistence pathways.
- Avoided introducing separate research-only storage models or isolated workflows.
- Promotion records include workflow and fingerprint metadata for provenance and duplicate control.

## Known Constraints

- Entity research execution currently uses one worker per request and does not expose user-driven cancellation.
- Reliability hardening focused on deterministic promotion and partial-failure visibility; deeper retry/backoff policy is still a candidate for the next sprint.

## Recommended Next Slice

Sprint 4.1 follow-up:
- add explicit cancel support for in-flight research workers
- add provider-level retry/backoff policy controls
- add richer evidence filtering in the Entity Research panel
- add export-time evidence drill-down links for analyst review packages
