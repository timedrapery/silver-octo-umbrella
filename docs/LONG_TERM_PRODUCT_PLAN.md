# Long-Term Product Plan

## 1. Product vision

silver-octo-umbrella should evolve into a unified, local-first OSINT workstation where an analyst can move from mission intake to archival closure without leaving one coherent desktop environment.

The end-state is not a toolbox of disconnected panels. It is a repeatable investigation system with:
- clear step-by-step workflow
- durable case continuity
- provenance-rich evidence handling
- chronology-aware reporting
- retention-friendly case organization

## 2. Core workflow pillars

1. Mission intake and planning
- define objective, scope, constraints, hypotheses, and legal/operational notes

2. Structured collection
- target handling, guided search workflows, adapters, and provider-backed entity research

3. Review and promotion
- triage findings, annotate signals, and promote durable evidence with provenance

4. Chronology and continuity
- maintain case activity narrative that ties actions together over time

5. Reporting and handoff
- deliver analyst and stakeholder-ready outputs grounded in chronology and traceability

6. Archive and retention
- close, package, and retain cases cleanly for future reference and reactivation

## 3. What already exists in the repository

Current foundational capabilities:
- case CRUD with durable local storage
- target and note management
- modular adapter investigations with run history and traceability
- finding triage with durable review state and analyst notes
- guided search builder with saved search lifecycle
- entity research with multi-source orchestration and evidence promotion
- provenance-rich entities/evidence storage model
- chronology-capable timeline generation (Sprint 5)
- chronology-aware reporting (Sprint 5)
- migration-safe schema evolution patterns

## 4. Gaps that still remain

Key gaps before one-stop-shop maturity:
- no dedicated mission intake dashboard/workspace
- targets and entities remain in separate surfaces
- no case-level workflow state machine (intake, collection, review, reporting, archive)
- no first-class attachments/screenshot/document capture workflow
- no case bundle portability export/import path
- no retention and archive operations with policy guidance
- no provider/plugin management UI for operational readiness
- no environment health diagnostics for configuration, network policy, and dependency readiness

## 5. Recommended major milestones

## Milestone 1: Mission intake and case dashboard (foundational)

Outcomes:
- mission intake panel with objective, hypotheses, risk/constraints, and task checklist
- case dashboard summarizing timeline health, unresolved high-risk findings, search/research activity, and evidence growth
- explicit workflow stage transitions for operational clarity

## Milestone 2: Unified target/entity workspace (foundational)

Outcomes:
- merged navigation surface for targets and entities
- pivot operations linking findings, searches, runs, and evidence from one place
- confidence/context overlays to reduce analyst context switching

## Milestone 3: Evidence and finding convergence (foundational)

Outcomes:
- structured pathways to correlate findings and evidence
- confidence scoring and analyst decision states
- stronger promotion and correlation controls for repeatable triage-to-evidence flow

## Milestone 4: Reporting and case package exports (high-value)

Outcomes:
- role-specific report modes (analyst, leadership, legal)
- chronology-first case package export (report + machine-readable artifacts + provenance)
- reproducible case handoff bundle for audits and team continuity

## Milestone 5: Archive, retention, and portability (foundational)

Outcomes:
- archive/restore lifecycle with retention metadata
- local portability for offline transfer and long-term storage
- cleanup and maintenance workflows to avoid stale-case sprawl

## Milestone 6: Operational readiness and plugin management (optional but strategic)

Outcomes:
- provider/plugin registry with health and configuration checks
- environment diagnostics (timeouts, proxy health, dependency checks)
- safer scaling from mock providers to controlled real integrations

## 6. Dependencies and sequencing

Recommended order and rationale:
1. Intake + dashboard first: creates operational framing for all later actions.
2. Unified target/entity next: removes core workflow fragmentation.
3. Evidence/finding convergence next: strengthens analyst decisions and auditability.
4. Reporting package upgrades next: turns workflow into repeatable deliverables.
5. Archive/retention next: secures long-term case value and cleanliness.
6. Plugin/ops management after foundations: avoid premature complexity.

## 7. Foundational vs optional features

Foundational (must-have for workstation coherence):
- mission intake/dashboard
- unified target/entity workspace
- evidence/finding convergence
- chronology-first reporting package
- archive and retention workflows

Optional/strategic (valuable but not blocking baseline maturity):
- advanced plugin marketplace/manager
- live external provider onboarding UI
- collaborative multi-analyst assignment and review routing

## 8. Risks to avoid

1. Fragmentation risk
- adding new panels without shared service-layer workflow contracts

2. Duplicate subsystem risk
- parallel data models for timeline, evidence, targets, or searches

3. Stability regression risk
- unbounded async workflows and timeout-free integrations

4. Reporting bloat risk
- adding sections without narrative structure and chronology focus

5. Storage drift risk
- schema changes without safe migration defaults and backfills

6. UI-only business logic risk
- critical workflow behavior implemented in widgets instead of services

## 9. Implementation principles for future milestones

- service-first logic, GUI-thin orchestration
- durable and typed records over transient state
- chronology and provenance as first-class outputs
- deterministic async boundaries (timeouts, failure isolation, predictable completion)
- iterative coherence over feature sprawl
