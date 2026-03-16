# silver-octo-umbrella

Local-first desktop investigation workbench built with Python and PySide6.

The application supports a complete analyst loop:
- create and manage cases
- add targets and notes
- run modular adapters against targets
- review findings with filtering and detail views
- inspect entity relationships in a graph
- export case reports (HTML, JSON, CSV)

All built-in adapters are currently offline mock adapters. The GUI, services, storage, workflow orchestration, and reporting are real.

## Product status

The repository is now beyond basic scaffold state and includes an end-to-end, persisted adapter execution history workflow.

Recent sprint uplift:
- standardized adapter execution metadata per run (status, timings, duration, finding count, error)
- resilient partial-failure behavior (one adapter can fail without aborting investigation)
- finding-to-run traceability via `adapter_run_id`
- persisted adapter run history attached to cases
- report run-log section tied to persisted run records

Sprint 2.1 findings triage uplift:
- durable finding review states (`NEW`, `REVIEWED`, `FLAGGED`, `DISMISSED`)
- persisted analyst notes per finding
- service-backed filtering and sorting for triage workflows
- findings workspace with quick triage actions and richer provenance-focused detail view
- case-level triage summary metrics (including high/critical unreviewed count)
- report sections for flagged and dismissed findings with triage-state breakdown

Sprint 3 guided search builder uplift:
- novice-friendly guided search workspace for structured Google query construction
- service-backed query generation with explanations and browser handoff URLs
- reusable query recipes for common OSINT discovery intents
- persisted case-linked saved searches with load, duplicate, and delete lifecycle actions
- case-level guided search activity metrics
- report section for guided search activity (query, rationale, intent, provider, notes)

Sprint 4 entity research and promotion uplift:
- case-native Entity Research workspace tab for email/IP/username investigation
- concurrent multi-provider orchestration review with provider execution metrics
- analyst-grade structured review queue with provenance and key-field visibility
- evidence promotion controls with reliability grading and analyst-note attachment
- duplicate-safe promotion pipeline with deterministic fingerprinting
- case-level entity research continuity metrics surfaced in the Cases panel
- report sections for entity research activity and promoted research evidence

Sprint 5 timeline and reliability hardening uplift:
- unified case activity timeline service covering searches, runs, findings, research, and evidence milestones
- dedicated Timeline workspace tab with chronological event drill-in
- case panel recent-activity view for fast continuity checks
- chronology-aware report section that communicates investigation progression over time
- deterministic timeout boundaries for adapter runs and provider queries to reduce hang-prone behavior

Sprint 6 mission and dashboard uplift:
- durable mission intake model (mission brief, objectives, hypotheses, scope, constraints, risk and legal notes)
- explicit persisted workflow stages (`INTAKE`, `COLLECTION`, `REVIEW`, `REPORTING`, `ARCHIVE_READY`)
- case dashboard with timeline health, high-risk pressure, search/research activity, evidence growth, and readiness signals
- guided next actions and checklist-based workflow support to reduce operator overwhelm
- featured high-value collection pivots (reverse phone lookup, email pivots, username pivots) integrated with Entity Research and Search Builder
- improved non-technical desktop usability with in-app quick start guidance and clearer first-run messaging

Sprint 7 unified lead workspace uplift:
- merged Lead Workspace tab that unifies targets and entities into one subject-of-interest surface
- durable lead lifecycle model (`NEW`, `ACTIVE`, `NEEDS_REVIEW`, `CORROBORATED`, `DEPRIORITIZED`, `CLOSED`)
- lead profile metadata for priority, owner, confidence, context, blocker notes, and mission relevance
- lead pivot drill-ins linking findings, evidence, searches, runs, and timeline activity from one place
- task-to-lead linkage so mission checklist execution is tied to concrete operational subjects
- lead-aware blocker/readiness explainers to reduce "not ready" ambiguity

Sprint 8 evidence/finding convergence uplift:
- durable finding-to-evidence correlation links with rationale, origin, and support confidence
- explicit analyst decision state on findings (`PENDING_REVIEW`, `CORRELATED`, `PROMOTED`, `NEEDS_MORE_SUPPORT`, `LOW_CONFIDENCE`, `DISMISSED`, `NOT_ACTIONABLE`)
- confidence-aware triage workflow with finding decision updates persisted and report-visible
- structured findings workflow actions to correlate against existing evidence or promote findings into new evidence
- first-class evidence attachment support for screenshots/files and URL-based public-media references
- integrated public-web source platform context (including YouTube/Instagram/Snapchat/Facebook/Threads URL capture)
- lead and dashboard support-maturity signals (correlated findings, unsupported findings, low-confidence backlog, unlinked evidence)
- attachment-aware readiness signals (evidence missing support artifacts)
- convergence-aware report sections for supported claims and unresolved support gaps

## Quick start

### Requirements
- Python 3.12+
- pip

### Install

```bash
git clone https://github.com/timedrapery/silver-octo-umbrella.git
cd silver-octo-umbrella
pip install -r requirements.txt
```

### Run app

```bash
python app/main.py
```

### Run tests

```bash
python -m pytest tests/ -v
```

## Investigation workflow

1. Open the Cases tab and create a case.
2. Add one or more targets and notes.
3. Open Investigation tab, choose target type and value.
4. Run either selected adapters or a preset.
5. Review findings and adapter outcomes.
6. Open Findings tab for triage actions, aggressive filtering, sorting, and analyst notes.
7. Open Search Builder tab to generate guided advanced searches and save them to the case.
8. Open Entity Research tab to run provider-backed research and promote selected evidence.
9. Open Lead Workspace tab to manage lifecycle state and pivot from each lead to findings, evidence, searches, runs, and timeline context.
10. Use Lead Workspace quick actions for reverse phone lookup, email pivots, and username pivots.
11. Open Findings tab detail area to set decision state/confidence, correlate findings to existing evidence, or promote findings into durable evidence.
12. Add screenshot/file attachments to evidence and capture public-media references by URL from the Findings workflow.
13. Open Timeline tab to review chronology, including decision, correlation, and attachment capture activity.
14. Open Graph tab for relationship visualization.
15. Export report in Reports tab.

## Architecture overview

- `app/models`:
  - domain models for case, target, finding, notes, evidence, adapter runs
- `app/storage`:
  - SQLite persistence and schema compatibility checks
- `app/services`:
  - case lifecycle, adapter orchestration, findings triage, normalization, graph derivation, reporting
- `app/core/adapters`:
  - adapter contract and built-in mock adapters
- `app/gui`:
  - desktop UI panels and background worker orchestration
- `app/reports/templates`:
  - report templates
- `tests`:
  - model, adapter, service, and storage coverage

## Adapter execution observability

Each adapter execution now emits and persists a run record with:
- run id
- adapter name
- target id
- status (`COMPLETE` or `FAILED`)
- started and completed timestamps
- duration in seconds
- finding count
- error message (if failed)

Each finding produced by an adapter run now includes `adapter_run_id`, enabling traceability from finding to concrete run instance.

## Reporting model

HTML report includes:
- mission framing section with workflow stage and checklist progress
- operational snapshot with timeline health, risk pressure, and pivot activity maturity
- case summary metrics
- triage-state breakdown
- flagged findings section
- active (non-dismissed) findings queue
- dismissed findings section
- guided search activity section
- case activity timeline section
- phone/email pivot activity counters
- entity research workspace activity section
- promoted research evidence section
- finding-evidence convergence summary section
- evidence attachments/public-media reference section
- major supported findings section with confidence and rationale context
- evidence needing finding correlation section
- subjects of interest section with lifecycle/priority/confidence/context and link coverage
- targets and notes
- discovered entities
- findings with review state and run linkage
- finding run IDs
- adapter run log with status/timing/error details
- source citations

JSON report exports full case model. CSV report exports flattened finding rows.

## Mock adapters and extension path

Built-in adapters (`dns`, `cert`, `http`, `social`, `subdomain`, `metadata`) are mock-only by design and do not make live network calls.

To add a new adapter:
1. Create adapter class under `app/core/adapters` inheriting from `BaseAdapter`.
2. Set `name`, `description`, and `supported_target_types`.
3. Implement `async run(target)` returning a list of `Finding`.
4. Register adapter in main window service setup.
5. Optionally include it in investigation presets.

The current adapter contract is intentionally compatible with future real integrations.

## What is intentionally not solved yet

- multi-target batch investigations
- case bundle import/export
- multi-analyst assignment and triage audit timeline
- network-backed real adapters

## Documents

- Implementation plan: `docs/IMPLEMENTATION_PLAN.md`
- Sprint summary: `docs/SPRINT_1_SUMMARY.md`
- Sprint 2.1 plan: `docs/SPRINT_2_1_PLAN.md`
- Sprint 2.1 summary: `docs/SPRINT_2_1_SUMMARY.md`
- Sprint 3 plan: `docs/SPRINT_3_PLAN.md`
- Sprint 3 summary: `docs/SPRINT_3_SUMMARY.md`
- Sprint 4 plan: `docs/SPRINT_4_PLAN.md`
- Sprint 4 summary: `docs/SPRINT_4_SUMMARY.md`
- Sprint 5 plan: `docs/SPRINT_5_PLAN.md`
- Sprint 5 summary: `docs/SPRINT_5_SUMMARY.md`
- Sprint 6 plan: `docs/SPRINT_6_PLAN.md`
- Sprint 6 summary: `docs/SPRINT_6_SUMMARY.md`
- Sprint 7 plan: `docs/SPRINT_7_PLAN.md`
- Sprint 7 summary: `docs/SPRINT_7_SUMMARY.md`
- Sprint 8 plan: `docs/SPRINT_8_PLAN.md`
- Sprint 8 summary: `docs/SPRINT_8_SUMMARY.md`
- Long-term product plan: `docs/LONG_TERM_PRODUCT_PLAN.md`
