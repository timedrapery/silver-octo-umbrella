# Sprint 6 Summary

## 1. What changed

Sprint 6 delivered Milestone 1 foundation as one coherent workflow slice:
- durable mission intake model added to case records
- explicit persisted workflow stage progression added
- service-driven case dashboard and guided recommendations added
- featured entity-driven pivots elevated (reverse phone lookup and email pivots)
- non-technical usability improvements added for first-run and navigation clarity
- report framing updated with mission/workflow maturity context

## 2. How mission intake works

Mission intake is now part of each case, not a parallel subsystem.

`MissionIntake` stores:
- mission summary
- objectives
- hypotheses
- scope
- constraints
- legal and operational notes
- risk notes
- priority
- intake notes
- task checklist
- intake timestamps

Case service exposes typed APIs to update intake fields and manage mission tasks.
Storage persists mission intake as structured JSON on the `cases` record with migration-safe defaults.

## 3. How workflow stage works

Workflow stage is explicit and durable through `WorkflowStage`:
- `INTAKE`
- `COLLECTION`
- `REVIEW`
- `REPORTING`
- `ARCHIVE_READY`

Each case also stores:
- stage note
- stage-updated timestamp

Case service enforces lightweight transition validation so progression remains intentional without overengineering a rigid state machine.

## 4. How the dashboard helps the user operate the case

Case dashboard now provides operational legibility in one surface:
- mission context and stage state
- timeline health and recent activity count
- unresolved high-risk pressure and flagged/new finding pressure
- search/research/evidence momentum
- checklist completion and reporting readiness
- concise recent activity feed from timeline service

Dashboard signals are derived in service logic, keeping GUI rendering thin and consistent.

## 5. How reverse phone lookup and email search are featured

Featured collection pivots are now prominent and integrated with existing workflows:
- Entity Research supports `PHONE` as first-class entity type for reverse phone lookup
- Entity Research quick action buttons highlight Phone, Email, and Username pivots
- Dashboard shows featured collection actions and candidate-driven pivot prompts
- Guidance recommends phone and email pivots when leads exist but coverage is incomplete
- Email pivoting is reinforced via Search Builder recommendations (Email Mention intent)

No one-off pivot subsystem was added; all actions route through existing case/research/search continuity.

## 6. What was improved for regular desktop app usability

Sprint 6 improved non-technical usability by reducing reliance on external docs/terminal assumptions:
- first-run status message points users to creating the first case
- in-app Help -> Quick Start flow explains practical startup steps
- dashboard onboarding hint provides state-aware "what to do next" guidance
- user-facing pivot copy emphasizes operational actions over developer jargon

## 7. How guided workflow support reduces operator overwhelm

Guidance is now condition-aware and concise:
- mission completeness checks
- stage-aware progression prompts
- high-risk/flagged pressure alerts
- stale timeline nudges
- phone/email pivot recommendations when actionable leads are detected
- archive/reporting blocker warnings

This shifts the app from passive storage to active workflow support.

## 8. Service/storage/model improvements

Model:
- `MissionIntake`, `MissionTask`, `MissionPriority`, `WorkflowStage`
- `EntityKind.PHONE`

Storage:
- migration-safe `cases` columns for mission intake JSON and workflow stage metadata
- backfilled defaults for legacy databases

Service:
- mission intake update API
- checklist task CRUD/update API
- workflow stage transition API
- dashboard summary API with pressure/readiness/momentum aggregation
- featured collection action generation and onboarding hints
- phone/email lead extraction for pivot recommendations

## 9. Tests added or improved

Added/updated deterministic tests for:
- mission intake defaults and task validation
- workflow stage defaults and transitions
- mission/stage schema migration and round-trip persistence
- dashboard summary and recommendation behavior
- phone/email pivot recommendation surfacing
- orchestrator phone request validation and type inference
- report mission/workflow/operational snapshot rendering, including phone/email pivot metrics

## 10. Tradeoffs and deferred work

- Reverse phone lookup currently depends on operator-supplied provider coverage or public pivots; the platform no longer fabricates offline fallback results.
- Guidance is intentionally lightweight and heuristic-based; full workflow policy engines are deferred.
- Stage transitions remain practical and editable; strict gate enforcement for every artifact is deferred.

## 11. Recommended Sprint 7

Sprint 7 should focus on mission execution depth:
- structured lead lifecycle and ownership states
- stage blocker drill-ins and readiness explainers
- richer task-to-artifact linkage (findings/searches/research evidence)
- role-oriented output modes for operator vs stakeholder audiences
