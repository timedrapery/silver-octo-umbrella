# Sprint 4 Plan

## 1. Current state after Sprint 3 plus core intelligence modules
- Case workflow, findings triage, adapter run observability, and guided search are fully integrated into the desktop UI.
- Core intelligence backend modules now exist and are typed:
  - managed outbound network client
  - async multi-source orchestrator
  - intelligence repository for entities/evidence
  - entity/evidence provenance fields in case models
  - migration-safe SQLite schema support
- Major gap: orchestrator and evidence-ledger capabilities are not yet exposed through a first-class operator workflow in the GUI.
- Evidence provenance fields exist in storage/model, but analysts cannot currently promote orchestrated results through a structured UI pathway.

## 2. Why entity research is the next critical operator-facing workflow
- Investigators need an immediate path from an entity lead (email/IP/username) to reviewed, durable intelligence.
- Without an integrated entity workspace, intelligence modules remain backend-only and analysts lose continuity between discovery and evidence capture.
- Product value increases when research actions are case-native, attributable, and report-visible.

## 3. Biggest workflow gaps blocking productization
- No case-integrated entity research tab invoking the orchestrator.
- No structured review surface for provider results and execution metrics.
- No deliberate promotion action from reviewed result item into durable evidence.
- No visible activity metrics for researched entities and promoted orchestration evidence in case summary surfaces.
- Async worker seam for investigations has a payload-shape edge case and no shared pattern for additional async workflows.

## 4. Sprint 4 scope
- Add a dedicated Entity Research workspace panel integrated into main tabs and current-case lifecycle.
- Implement service-layer transformation utilities for readable result summaries and evidence-promotion payload construction.
- Wire orchestration execution into the panel with:
  - entity input/type inference
  - provider execution metadata display
  - normalized result review table + details pane
  - promote-selected-to-evidence action (single and multi-select)
- Persist research artifacts via existing intelligence repository:
  - create/update entities linked to case
  - create evidence with provenance and normalized summary
- Add practical duplicate-promotion protection.
- Extend case-level summary metrics to include researched entities and orchestration-derived evidence.
- Uplift report output with researched entity and promoted evidence sections.
- Add async stability hardening for blocking reliability issues related to this flow.
- Add tests for research review, promotion, linkage, dedup behavior, and report visibility.

## 5. Acceptance criteria
- Analyst can run entity research for EMAIL/IP/USERNAME from a case-integrated workspace.
- UI shows provider execution metadata and normalized result summaries in a review-friendly layout.
- Analyst can promote selected result items into durable case evidence.
- Evidence records preserve case_id, entity linkage, source reliability, raw_json_data, normalized_summary, and provider attribution.
- Duplicate promotions for the same entity/provider/result fingerprint are prevented where practical.
- Case summary surfaces include researched entity and promoted-evidence signals.
- Reports include researched entities and promoted evidence provenance/timestamps.
- New workflow logic is covered by tests and passes.

## 6. Risks and tradeoffs
- Provider payloads are heterogeneous; normalization will prioritize concise analyst summaries over exhaustive field mapping.
- Multi-select promotion increases usability but requires careful dedup logic to avoid noisy evidence stores.
- Async hardening will focus on workflow-blocking stability issues, not a full threading/runtime redesign.

## 7. Recommended next sprint
- Add longitudinal activity timeline combining investigations, guided searches, entity research, and evidence promotions.
- Add analyst assignment/review ownership for promoted evidence.
- Add advanced dedup heuristics and merge workflows for repeated research over time.
