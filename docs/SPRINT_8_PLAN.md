# Sprint 8 Plan

## 1. Current product state after Sprint 7

The workstation has a durable, service-led baseline:
- case CRUD with migration-safe SQLite persistence
- investigation runs with run telemetry and finding traceability
- finding triage with review state and analyst notes
- entity research with evidence promotion and provenance metadata
- guided search persistence and timeline-aware operations
- mission intake, checklist tasks, and workflow stage progression
- unified lead workspace with lifecycle, blockers/readiness, and task linkage
- dashboard recommendations and chronology-aware reporting

Findings and evidence are both durable, but they are still mostly related by ad hoc inference (text overlap, finding_id fields, and lead aggregation heuristics) rather than explicit convergence records and analyst-reviewed support decisions.

## 2. Why evidence/finding convergence is the next foundational layer

Milestone 3 requires practical investigation reasoning support, not only artifact collection.

The next foundational layer is explicit signal-support convergence:
- findings represent claims/signals requiring adjudication
- evidence represents support/provenance requiring context
- analysts need durable, explainable links and decision state to move from triage to reporting

Without this layer, reporting readiness and lead confidence remain partly inferred from volume rather than support quality.

## 3. Current friction in the triage-to-evidence path

- no first-class workflow for correlating a finding to existing evidence
- no durable rationale record for why a finding and evidence item are linked
- promotion paths exist (especially research promotion) but are not unified with finding adjudication
- duplicate-prevention is provider-fingerprint specific in entity research but not generalized for finding-driven promotion
- triage actions and evidence actions are in separate UI contexts, increasing analyst context switching

## 4. Current gaps in correlation visibility and analyst decision support

- no durable many-to-many support map between findings and evidence
- no explicit decision state focused on convergence outcomes
- no confidence/state model dedicated to support maturity
- lead blockers/readiness can see finding/evidence counts but not support quality gaps
- report sections show findings and evidence but not strong claim-to-support mapping and maturity summary

## 5. How screenshot and public-media evidence collection fits this sprint without fragmenting the product

Screenshot and URL/public-media capture must stay inside evidence workflows:
- capture artifacts as evidence attachments linked to existing evidence IDs
- allow URL-based public-media capture to create or enrich evidence records in-place
- preserve provenance metadata (source URL, source platform, analyst note, capture timestamps)
- keep workflow user-driven from findings/evidence context; no hidden or background collection
- avoid a standalone downloader subsystem or platform-specific automation sprawl

This keeps capture durable, explainable, and report-ready while preserving the existing case/entity/evidence architecture.

## 6. Sprint 8 scope

1. Convergence domain model and durable linkage
- add typed durable finding-evidence correlation records per case
- persist link rationale, support strength/confidence, origin metadata, and timestamps
- keep evidence/finding systems as-is and add one integrated linkage layer

2. Analyst decision and confidence model
- add lightweight decision state for finding support lifecycle
- support confidence score or confidence band and explicit analyst rationale
- persist decision updates durably with last-decision timestamp

3. Triage-to-evidence convergence workflow APIs
- correlate finding to existing evidence
- promote finding into new evidence with deliberate rationale/confidence
- fetch evidence supporting a finding and findings supported by an evidence item
- prevent redundant promotion/link creation where practical

4. Lead workspace and finding surface integration
- expose convergence metrics in lead detail and list summaries
- highlight open findings without support and low-confidence signals
- show evidence/finding support context in finding detail workflow

5. Dashboard/readiness integration
- incorporate correlation quality into blocker/readiness and recommendations
- identify high-priority leads with weak support maturity
- tighten reporting-readiness heuristics using convergence coverage

6. Reporting uplift
- add concise correlated findings/evidence section
- show confidence and rationale summaries for major supported findings
- show unresolved weak/uncorroborated signals without report bloat

7. Tests and docs
- add deterministic model/storage/service/report tests for new convergence behavior
- document Sprint 8 implementation and operational value

## 7. Acceptance criteria

- finding-evidence links are explicit, durable, and queryable both directions
- analysts can correlate and promote through typed service APIs with rationale and confidence
- finding decision state and confidence are explicit, persisted, and updateable
- duplicate link/promotion prevention works for obvious redundant actions
- screenshot/file attachments are durable, case-linked evidence support artifacts
- URL-based public-media references can be captured into evidence with provenance metadata
- lead workspace reflects support maturity and unresolved low-confidence/open-support gaps
- dashboard/blocker/readiness logic incorporates convergence quality signals
- report output includes correlated claim-support context and confidence summaries
- all core convergence logic is covered by deterministic tests below GUI layer

## 8. Risks / tradeoffs

- over-linking risk from loose heuristics: default to analyst-confirmed linking, with conservative auto-inference
- model complexity risk: keep decision taxonomy lightweight and operational
- report verbosity risk: include only high-value support summaries and key unresolved gaps
- platform-specific capture brittleness risk: keep public-media collection URL-driven in Sprint 8
- migration risk: schema changes must be additive and backfilled safely

## 9. Recommended Sprint 9

Sprint 9 should deepen execution quality after convergence baseline:
- assignment/ownership workflows for finding decisions and support tasks
- saved review queues (for example unsupported flagged findings)
- confidence trend tracking and stale-support alerts
- targeted collaboration/audit improvements for analyst handoffs

## 10. How Sprint 8 directly fulfills Milestone 3

Milestone 3 outcomes map directly:

1. Structured pathways to correlate findings and evidence
- implemented via durable finding-evidence link model and correlation APIs

2. Confidence scoring and analyst decision states
- implemented via persisted decision state and confidence on finding support lifecycle

3. Stronger promotion and correlation controls for repeatable triage-to-evidence flow
- implemented via deliberate promotion/correlation workflow with rationale, duplicate guards, and bidirectional retrieval for review and reporting
