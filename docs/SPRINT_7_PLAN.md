# Sprint 7 Plan

## 1. Current product state after Sprint 6

The workstation already has a durable investigation backbone:
- case CRUD with migration-safe SQLite persistence
- mission intake, checklist tasks, and explicit workflow stages
- adapter investigations with run telemetry and finding-to-run linkage
- finding triage with analyst notes and service-backed filtering/sorting
- guided search builder with saved-search lifecycle
- entity research with multi-provider orchestration and evidence promotion
- evidence and entity durability with provenance-rich fields
- timeline service and timeline tab for chronology
- report framing with mission/workflow and operational snapshots
- stage-aware dashboard recommendations and featured phone/email pivots

This is the baseline architecture and Sprint 7 will extend it directly.

## 2. Why target/entity unification is the next foundational layer

Current capability is broad but navigation is still split by subsystem:
- targets are managed from case and investigation entry points
- entities are managed from research workflows
- pivotable artifacts (searches/findings/evidence/runs/timeline) are spread across tabs

A unified lead workspace is the next foundational layer because it shifts analyst thinking from storage origin to operational subject:
- one lead surface for people, usernames, emails, phones, domains, IPs, and related subjects
- one pivot pane to inspect what has been done and what is missing
- one place to update lifecycle, priority, confidence, and blockers

## 3. Current fragmentation and context-switching pain points

- No merged case surface for targets and entities.
- Lead status is implicit and inferred from counts, not explicit and actionable.
- Relationship drill-ins require tab-hopping between search, research, findings, evidence, and timeline.
- Readiness signals are case-level but not lead-level, so operators lack subject-specific guidance.
- Mission tasks are durable but weakly linked to concrete leads/artifacts.

## 4. How Sprint 6 recommendations fit into Sprint 7

Sprint 6 recommended deeper mission execution support through:
- structured lead lifecycle and ownership states
- stage blocker drill-ins and readiness explainers
- richer task-to-artifact linkage

Sprint 7 implements these as a unified lead operating model:
- persistent lead profile state (lifecycle/priority/owner/confidence/context)
- lead-specific blocker and readiness explanations from real artifact conditions
- durable task-to-lead and task-to-artifact links for mission execution traceability

## 5. Sprint 7 scope

1. Unified lead domain and persistence
- add durable lead profile records linked to case
- add durable mission task link records to connect tasks with leads/artifacts
- keep target/entity systems intact and derive lead unification from them

2. Unified lead service layer
- synchronize lead records from existing targets/entities
- provide typed lead listing/filtering/sorting APIs
- aggregate related searches, research activity, findings, evidence, runs, and timeline for a selected lead
- expose lead lifecycle/profile update APIs
- expose blocker/readiness explanation APIs
- expose task-link APIs

3. Unified workspace UI
- add dedicated lead workspace tab as a mission-execution pivot hub
- merged lead list with lifecycle/priority/confidence/activity signals
- detail pane with artifact pivot summaries and blocker/readiness explanations
- quick actions for reverse phone lookup, email pivots, username pivots, and tab jumps
- controls to update lifecycle/profile metadata and attach mission tasks

4. Reporting uplift
- add concise lead-centric section covering key leads, lifecycle state, confidence/context, and correlated artifact activity

5. Documentation and tests
- deterministic service/storage tests for lead sync, lifecycle updates, artifact aggregation, blocker logic, and task-link behavior
- report assertions for lead-centric output
- Sprint 7 summary + README updates

## 6. Acceptance criteria

- Unified lead list merges target/entity perspectives into one practical subject surface.
- Lead lifecycle is explicit, durable, and updateable via typed service APIs.
- A selected lead can pivot to related searches, research, findings, evidence, runs, and relevant timeline events.
- Blocker/readiness drill-ins explain missing actions using real artifact conditions.
- Mission tasks can be linked to leads/artifacts durably.
- Workspace uses plain operational language with strong empty states and obvious quick actions.
- Report includes concise lead-centric intelligence framing.
- New logic is covered by deterministic non-UI tests.

## 7. Risks / tradeoffs

- Lead normalization must avoid over-aggressive merging; conservative canonicalization is preferred.
- Correlation heuristics (especially free-text matching) may produce partial links; links should be explainable.
- Adding persistence for lead/task links introduces migration and integrity considerations.
- UI must stay operationally useful without overloading operators with dense artifact detail.

## 8. Recommended Sprint 8

Sprint 8 should focus on execution depth and multi-operator maturity:
- assignment workflows and reviewer ownership for leads/tasks
- richer corroboration scoring and evidence quality thresholds
- saved lead views and mission lane boards
- lead-specific chronology narratives for reporting modes

## 9. How Sprint 7 fulfills Milestone 2

Milestone 2 requires:
1. merged navigation surface for targets and entities
2. pivot operations linking findings, searches, runs, and evidence from one place
3. confidence/context overlays to reduce analyst context switching

Sprint 7 fulfills this directly by:
- introducing a unified lead workspace backed by durable lead profiles
- adding service-level artifact aggregation and pivot drill-ins per lead
- adding lifecycle/priority/confidence/context and blocker overlays as first-class lead metadata
- linking mission tasks to leads/artifacts for execution continuity
