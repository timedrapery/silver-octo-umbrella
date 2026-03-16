# Sprint 6 Plan

## 1. Current product state after Sprint 5

The workstation already supports durable case execution loops:
- case CRUD, targets, notes, and persistent adapter-run history
- finding triage lifecycle with analyst notes and severity/state filtering
- guided search builder with saved-search persistence
- entity research with provider metrics and evidence promotion
- provenance-rich entities/evidence storage and migration-safe schema updates
- unified timeline generation and timeline-aware reports

The architecture is already service-led and typed. Sprint 6 must extend this backbone, not bypass it.

## 2. Why mission intake and case dashboarding are the next foundational layer

Current workflows capture artifacts well but still create operator friction at case start and case handoff:
- case purpose, scope, and constraints are not durable first-class records
- lifecycle stage is implied by data volume, not explicitly modeled
- key pressure/readiness signals are spread across tabs and must be mentally merged

Mission intake plus stage-aware dashboarding is the shortest path to Milestone 1 coherence:
- gives each case explicit mission intent and boundaries before collection begins
- makes lifecycle maturity visible and durable
- reduces context-switch overhead by surfacing pressure, momentum, and next actions in one operational view

## 3. Current operator-friction and overwhelm problems

- No durable mission brief/objective/hypothesis structure per case.
- No explicit workflow stage progression (intake -> collection -> review -> reporting -> archive-ready).
- No stage-aware readiness checks to prevent premature progression.
- Dashboard-like signals exist but are fragmented (triage/search/research/timeline summaries in separate surfaces).
- No concise next-step guidance grounded in current case conditions.

## 4. How high-value entity-driven actions should be surfaced in Sprint 6

- Reverse phone lookup is elevated as a first-class entity research action (PHONE type) rather than hidden in free-form inputs.
- Email pivoting is surfaced in both Entity Research (EMAIL research path) and guided Search Builder recommendations (EMAIL_MENTION intent).
- Dashboard surfaces featured collection pivots so users can immediately launch high-value next moves.
- Guidance engine recommends phone/email pivots when candidate leads exist but have not been researched.

## 5. What currently makes the app feel too technical

- First-run behavior gives limited in-app onboarding; users must infer sequence from tabs.
- Advanced workflows are available but discoverability relies on analyst familiarity.
- Some user-facing copy assumes technical confidence rather than guided progression.

Sprint 6 addresses this with in-app quick-start guidance, clearer recommendation copy, and featured pivot visibility.

## 6. Sprint 6 scope

1. Mission intake domain model
- add durable mission-intake structure to case model
- include mission summary, objectives, hypotheses, scope, constraints, legal/operational notes, risk notes, priority/urgency, intake notes, and task checklist

2. Workflow stage model
- add explicit durable workflow stage field and stage metadata
- support intentional stage updates with lightweight transition validation

3. Service-layer dashboard + guidance logic
- add typed dashboard summary API in case service
- aggregate pressure/readiness/momentum signals from existing findings/search/research/evidence/timeline data
- generate concise stage-aware recommended next actions

4. UI integration
- extend case workspace with mission intake editing, stage controls, checklist visibility, dashboard signals, and recommended-next-actions block
- keep UI thin by consuming service APIs

5. Reporting uplift
- include mission and workflow framing in report output
- include concise operational maturity/pressure signals and recent activity summary

6. Testing
- model validation tests for mission/stage/checklist structures
- storage migration + persistence round-trip tests
- service tests for stage updates, dashboard signals, and guidance generation
- report tests for mission/workflow framing

## 7. Acceptance criteria

- Mission intake fields are durable, editable, and retrievable through case service APIs.
- Workflow stage is persisted and visible, with controlled updates through service APIs.
- Dashboard summary exposes operationally useful signals:
	- unresolved high-risk/flagged pressure
	- new/unreviewed workload
	- saved-search and research activity
	- evidence growth
	- timeline freshness/recent activity
- Case UI presents mission, stage, pressure, momentum, and next-step guidance in one coherent operational surface.
- Checklist/task items are durable and support update behavior.
- Reports include mission framing and workflow maturity signals without bloat.
- New logic is covered by deterministic tests.
- Reverse phone lookup and email pivot actions are visibly featured in case dashboard guidance.
- App startup and empty-state messaging improve first-use clarity for non-technical desktop users.

## 8. Risks and tradeoffs

- Avoid overengineering stage transitions into a rigid state machine that blocks practical analyst movement.
- Keep guidance concise; noisy recommendation lists reduce trust.
- Preserve migration safety: legacy databases must open with sensible defaults.
- Keep dashboard derivation service-level to avoid GUI divergence and duplicated rules.
- Keep pivot surfacing integrated with existing research/search flows; avoid creating one-off subsystems.

## 9. Recommended Sprint 7

Sprint 7 theme: Mission execution workflows and lead management.
- add explicit lead/task execution states linked to findings/search/research artifacts
- add ownership/assignment metadata for task accountability
- add stage-readiness explainers and blocker drill-in views
- add report mode options (operator snapshot vs stakeholder summary)

## 10. How Sprint 6 fulfills Milestone 1 of the long-term plan

Milestone 1 requires:
1. Mission intake panel with objective/hypotheses/risk/constraints/checklist.
2. Case dashboard with timeline health, unresolved high-risk pressure, search/research activity, and evidence growth.
3. Explicit workflow stage transitions.

Sprint 6 implementation maps directly:
- mission-intake model + case UI editor + durable checklist satisfy requirement 1
- service-derived dashboard and recent-activity synthesis satisfy requirement 2
- persisted stage model and service-updated transitions satisfy requirement 3

Result: the case becomes an operational mission record with clear purpose, lifecycle position, and guided next steps.
