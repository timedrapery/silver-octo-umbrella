# Sprint 7 Summary

## 1. What changed

Sprint 7 delivered Milestone 2 foundation by introducing a unified lead workspace that merges target/entity navigation and adds durable lead lifecycle operations.

Implemented:
- durable lead profile model and persistence (`leads` table)
- durable mission task to artifact linkage (`mission_task_links` table)
- unified lead service for cross-artifact pivots and blocker/readiness explainers
- Lead Workspace desktop tab with merged lead list, lifecycle editing, pivot drill-ins, and quick actions
- quick-pivot handoff wiring into Entity Research and Search Builder tabs
- dashboard recommendation improvements with lead-blocker signals
- report uplift with concise Subjects Of Interest section

## 2. How the unified target/entity workspace works

The Lead Workspace is a service-backed mission-execution hub:
- targets and entities are normalized into one lead profile per subject of interest
- each lead records canonical identity, kind, linked target IDs, linked entity IDs, and activity metadata
- the list surface supports practical filtering by type, lifecycle, priority, freshness, and artifact presence
- selecting a lead opens a pivot drill-in with linked findings, evidence, searches, runs, and timeline relevance

This keeps operators focused on subjects, not storage subsystems.

## 3. How lead lifecycle works

Lead lifecycle is explicit and durable via:
- `NEW`
- `ACTIVE`
- `NEEDS_REVIEW`
- `CORROBORATED`
- `DEPRIORITIZED`
- `CLOSED`

Each lead also supports:
- priority (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- owner/handler
- confidence score (0.0 to 1.0)
- context summary
- blocker note
- why-it-matters summary
- last activity timestamp

Updates are handled by typed service APIs and persisted in storage.

## 4. How the workspace reduces analyst context switching

Context switching is reduced by combining list + drill-in + quick actions in one place:
- one merged lead list for core subjects
- one detail view showing what has already happened across searches/research/findings/evidence/runs/timeline
- one-click actions for reverse phone lookup, email pivot search, username pivot search, and tab jumps
- mission task links visible directly on the lead

This shifts workflow from tab hunting to lead-centered execution.

## 5. How blocker/readiness drill-ins work

Lead blocker logic is generated from real case conditions, including:
- high-priority lead without evidence
- no entity-research activity for key lead types (phone/email/username/IP)
- unresolved flagged/high-risk findings tied to a lead
- missing search/task linkage context
- reporting-stage evidence gaps

Each lead now has readiness status (`READY`, `PARTIAL`, `BLOCKED`) plus concrete explanatory notes.

## 6. Service/storage/model improvements

Model additions:
- `LeadLifecycleState`
- `LeadPriority`
- `ArtifactLinkType`
- `LeadProfile`
- `MissionTaskLink`

Storage additions:
- `leads` table
- `mission_task_links` table
- CRUD and hydration support for leads/task links

Service additions:
- `LeadWorkspaceService` for lead sync, filtering, detail aggregation, lifecycle updates, task linking, and blocker/readiness explainers
- `CaseService` typed wrappers for lead and task-link operations

UI additions:
- `LeadWorkspacePanel` with merged list, profile editing, task linkage, blocker/readiness view, and quick pivot actions

## 7. Tests added or improved

Added:
- `tests/test_lead_workspace_service.py`
  - lead unification from targets/entities
  - lifecycle persistence updates
  - artifact aggregation in lead detail
  - blocker/readiness explainability
  - task-to-lead durable linkage

Updated:
- `tests/test_models.py` for lead profile and task-link model coverage
- `tests/test_storage.py` for leads/task-links table and round-trip persistence
- `tests/test_services.py` for case-service lead APIs and report lead-section assertions

## 8. Tradeoffs / deferred work

- Lead correlation currently uses conservative deterministic matching and lightweight text heuristics.
- Artifact pivot drill-ins are intentionally concise to preserve usability for non-technical operators.
- Advanced ownership routing (multi-analyst queues, assignment SLAs) is deferred.
- Per-lead evidence quality scoring beyond confidence/context fields is deferred.

## 9. Recommended Sprint 8

Sprint 8 should deepen execution governance:
- assignment and reviewer workflows for leads/tasks
- richer corroboration scoring and evidence quality thresholds
- saved lead views/queues for recurring operational modes
- expanded lead-centric reporting modes for analyst vs stakeholder audiences
