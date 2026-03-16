# Implementation Plan

## 1. Executive assessment
silver-octo-umbrella is a functional local-first desktop investigation platform with a working GUI, modular adapters, persistence, graphing, and report export. Core plumbing exists across models, services, storage, and tests.

It is not yet a credible V1 investigation workbench because adapter execution is weakly observable end-to-end: run-level metadata is not first-class in orchestration, finding-to-run lineage is missing, and failure behavior is not consistently surfaced as durable investigation history.

## 2. Key weaknesses (ranked by impact)
1. Adapter execution observability is fragmented.
- Storage and model support for adapter runs exists, but investigation orchestration returns only findings and drops structured run context.

2. Findings are not traceable to a specific adapter run.
- A finding records adapter name but not run identity, limiting auditability and confidence in repeated investigations.

3. Workflow continuity gap between investigation execution and case history.
- Runs are not consistently persisted from the active investigation flow, reducing trust in case chronology.

4. Reporting credibility gap for run history.
- The report includes run log sections in template logic, but run quality depends on missing orchestration linkage.

5. Tests under-represent the critical run-observability slice.
- Existing tests validate adapters and storage separately but do not verify the full service behavior of timing/status/error/run-to-finding linkage.

## 3. First sprint goal
**Sprint theme: Adapter run history + execution observability + findings traceability**

Create a coherent investigation execution pipeline where each adapter run is timed, statused, error-aware, persisted, and linked to produced findings.

## 4. Sprint scope
- Introduce a structured investigation execution result in service layer containing:
  - aggregated findings
  - per-adapter run records
  - run summary metrics (success/failure counts)
- Standardize run instrumentation per adapter:
  - started_at, completed_at, duration_seconds, status, finding_count, error_message
- Add finding-level run traceability:
  - new finding field for adapter_run_id
  - persistence round-trip in database
- Persist adapter runs from investigation workflow into case history when a case is active.
- Improve completion feedback to clearly communicate partial failures without aborting the workflow.
- Ensure reporting consumes persisted run history and remains coherent.
- Add tests for:
  - service-level run instrumentation (success and failure)
  - finding-to-run linkage
  - persistence of adapter_run_id and adapter runs

## 5. Acceptance criteria
- Running an investigation with at least one failing adapter still completes and returns successful findings.
- Each adapter execution produces a run record with status, timestamps, duration, and finding count.
- Each finding created during a run includes adapter_run_id matching an emitted run record.
- Adapter run records are persisted to the active case and are visible after case reload.
- Report output includes adapter run history for persisted runs.
- New behavior is covered by automated tests and test suite passes.

## 6. Risks and tradeoffs
- Not introducing multi-target batch execution in this sprint to preserve focus.
- Not redesigning the entire GUI information architecture; only targeted workflow messaging improvements are included.
- Existing adapters should remain contract-compatible while moving toward real collection and away from fabricated placeholder output.

## 7. Recommended next sprint
**Findings triage + filtering + review workflow**
- Add review state and analyst disposition fields.
- Add richer filtering/grouping/sorting at service level.
- Add case metrics dashboard for unresolved high-risk findings and review progress.
