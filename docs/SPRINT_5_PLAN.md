# Sprint 5 Plan

## 1. Current product state after Sprint 4

The repository now has an end-to-end case-centric workflow with durable persistence:
- investigation execution with adapter run history, partial-failure resilience, and finding-to-run linkage
- triage lifecycle with review states and analyst notes
- guided search builder with persisted case-linked search artifacts
- entity research workflow with provider metrics, reviewed result promotion, and provenance-rich evidence
- report output spanning findings, triage, searches, entities, promoted evidence, and run logs

The baseline architecture is service-led and typed, with SQLite-backed durability and migration-safe schema upgrades.

## 2. Why timeline/history is the next critical layer

Despite rich artifacts, the product still presents most workflows as sectioned snapshots rather than a coherent chronology.

Without a unified case timeline, analysts cannot quickly answer:
- what happened first versus later
- when pivots occurred
- how searches, runs, research, and evidence promotion progressed
- what changed recently and whether investigation momentum is healthy

A timeline layer is now the highest-leverage coherence feature because it turns completed slices into one investigation story.

## 3. Current reliability blockers

Primary blockers observed in current state:
- no explicit timeout boundary around adapter execution, which risks unbounded waits if an adapter stalls
- no explicit timeout boundary around provider queries in orchestrator execution
- brittle test/runtime behavior around timing expectations and slower Windows environments
- inconsistent payload shape safety in worker completion paths for no-adapter scenarios
- a correctness bug in main window case refresh wiring (indentation defect in triage update path)

## 4. Sprint 5 scope

1. Add case timeline domain service
- derive a unified event feed from durable case records (no parallel subsystem)
- support event type/category, timestamp, concise summary, and source references
- normalize events across case, search, investigation, findings, notes, entity research, and evidence promotion

2. Add timeline UI surface
- add a dedicated timeline/history tab integrated with current-case lifecycle
- provide readable chronological table + event detail pane
- include lightweight event filtering and recent-activity signal

3. Add chronology-aware reporting
- include case activity timeline section in HTML report
- keep section concise, readable, and investigation-story focused

4. Reliability hardening
- add deterministic timeout controls to investigation adapter execution
- add deterministic timeout controls to orchestrator provider execution
- ensure timeout and failure paths remain audit-friendly through existing run/provider metrics
- fix known main window wiring defect and worker no-adapter completion shape

5. Testing
- add service tests for timeline generation and ordering
- add chronology-aware report tests
- add timeout/partial-failure determinism tests for investigation and orchestrator logic
- keep behavior deterministic with fake providers/adapters

6. Documentation
- Sprint 5 summary
- long-term product plan with phased workstation roadmap
- README uplift for timeline and chronology-aware workflow

## 5. Acceptance criteria

- case timeline service returns coherent, descending chronology for a case from existing records
- timeline includes meaningful events from searches, runs, findings, notes, entity research, and promoted evidence
- timeline UI is integrated and readable, with event details and low-noise summaries
- HTML report includes a concise chronology section that communicates investigation progression
- investigation service enforces bounded adapter runtime and reports timeout failures cleanly
- orchestrator enforces bounded provider runtime and preserves partial-failure behavior
- no major regressions in existing workflows; new behavior covered by tests

## 6. Risks / tradeoffs

- derived timelines cannot represent true mutation history where historical records are not captured; summaries will reflect durable artifacts and available timestamps
- adding strict timeouts can surface new failed runs in edge cases; this is preferable to hidden indefinite stalls
- timeline readability depends on summary normalization quality; over-detailed events will create noise

## 7. Recommended Sprint 6

Sprint 6 theme: Mission intake and operational dashboard.
- add mission brief/intake model and UI
- add case dashboard with active leads, triage pressure, and chronology health indicators
- add guided workflow checklist to reduce operator overwhelm
- add explicit workflow state transitions (intake, active collection, review, reporting, archive-ready)

## 8. Longer-term product direction (next 3 to 5 major milestones)

Milestone A: Mission intake and dashboard
- mission brief, objectives, constraints, hypotheses, and legal/operational notes
- case dashboard with workflow progress and risk indicators

Milestone B: Unified target/entity workspace
- converge targets and entities into one navigation surface with relationship and evidence context
- faster pivoting between findings, searches, and promoted evidence

Milestone C: Evidence and finding convergence
- improve evidence/finding linkage workflows and confidence workflows
- add structured promotion and correlation paths for analyst decision support

Milestone D: Reporting and case package exports
- multi-audience reporting modes (analyst, management, legal)
- exportable case bundle with chronology, artifacts, and provenance

Milestone E: Archive and retention workflows
- archive lifecycle, retention metadata, cleanup prompts, and portability controls
- stable offline case portability and environment health validation
