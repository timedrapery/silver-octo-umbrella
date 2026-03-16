# Sprint 1 Summary

## 1. What changed
Sprint theme executed: **Adapter run history + execution observability + findings traceability**.

Implemented:
- structured investigation execution model in service layer (`InvestigationExecution`)
- per-adapter run instrumentation (`execute_adapter`) with status, timing, duration, finding count, and error capture
- finding-level traceability field (`Finding.adapter_run_id`)
- persistence round-trip for `adapter_run_id` in SQLite
- schema compatibility migration for existing local databases (adds missing `findings.adapter_run_id` column)
- case service method to persist adapter runs from investigation workflow
- GUI worker/main-window integration to carry run telemetry from execution into case persistence
- improved completion messaging showing adapter success/failure counts
- findings detail panel now shows adapter run ID
- HTML report template fixed and upgraded to include run-aware summary and adapter run log table with timestamps/status/error

## 2. Why it matters
The product now preserves investigation execution history as first-class case data. Analysts can answer:
- which adapter run produced this finding
- which adapters failed during a run
- how long each adapter took
- how many findings each adapter produced

This closes a major trust gap between running an investigation and auditing outcomes later.

## 3. Architecture improvements
- orchestration moved from flat finding collection to explicit execution result model
- adapter run instrumentation centralized in service layer instead of scattered GUI logic
- stronger service-to-storage contract for run metadata and finding lineage
- database schema migration step added for safe local upgrades

## 4. User-facing improvements
- investigations complete even with partial adapter failures, while failures are surfaced clearly
- status message includes adapter success/failure outcomes
- findings panel exposes run ID for traceability
- exported HTML report includes run-quality context and finding run linkage

## 5. Tests added or improved
Added/updated tests for critical sprint behavior:
- service-level run metadata and execution summary behavior
- partial failure isolation while preserving successful findings
- finding `adapter_run_id` persistence round-trip
- case service persistence of adapter runs
- model default assertion for finding traceability field

## 6. Documentation changes
- added implementation plan: `docs/IMPLEMENTATION_PLAN.md`
- rewrote `README.md` for technical credibility and accurate product state
- documented run observability model and traceability workflow
- documented current scope vs deferred roadmap items

## 7. Tradeoffs and deferred work
Intentionally deferred to keep sprint focused:
- multi-target batch runs
- advanced finding triage/review states
- case import/export bundles
- real network-backed adapters

## 8. Recommended next sprint
**Findings triage + filtering + review workflow**:
- add review state and analyst disposition fields
- service-level sorting/filtering/grouping utilities
- focused case metrics for unresolved high/critical findings
- report sections for triage status distribution
