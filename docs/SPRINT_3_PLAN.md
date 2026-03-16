# Sprint 3 Plan

## 1. Current product state after Sprint 2.1
- Case workflow, adapter execution observability, and finding triage are already durable and case-integrated.
- Findings now support review state, analyst notes, filtering, sorting, and triage-aware reporting.
- Service layer already carries business logic for triage and case summaries, reducing GUI coupling.
- The product still lacks a dedicated public-web discovery workflow for guided advanced search construction.

## 2. Why guided search is the next high-value workflow
- Discovery currently starts only from adapters and targets; non-technical users have no guided way to run high-quality public-web investigations.
- Advanced search syntax is high-leverage but inaccessible to novices without structured assistance.
- Case continuity improves when search intent, generated query, and rationale are saved and revisitable.
- Guided search closes a major workflow gap between case setup and finding review.

## 3. Sprint 3 scope
- Add durable saved-search data model connected to cases (and optionally targets).
- Add migration-safe persistence for saved searches in SQLite.
- Implement a dedicated search-builder service for:
  - structured Google-style query generation
  - plain-language explanation generation
  - input normalization and validation
  - recipe/template support for common investigation intents
- Build a novice-friendly Search Builder GUI workspace with:
  - structured controls
  - generated query preview
  - plain-language explanation
  - browser launch action
  - save-to-case workflow
  - saved searches list with reload/duplicate/delete
- Integrate case-level search metrics where useful.
- Extend report output with saved searches section.
- Add tests for service logic, persistence/migration, case linkage, recipes, and report output.

## 4. Acceptance criteria
- A user can create advanced Google-style queries via structured controls without writing operators manually.
- Generated query and plain-language explanation are shown together.
- Query can be launched in default browser.
- Search can be saved to current case with title/intent/notes/tags and optional target association.
- Saved searches can be revisited and reused in the Search Builder panel.
- Existing databases migrate safely and support saved search records.
- Report includes saved searches with query and explanation context.
- Core query generation and persistence behavior are covered by tests.

## 5. Risks / tradeoffs
- Scope is focused on browser handoff and case continuity, not scraping automation.
- Recipe set will remain intentionally small and polished to avoid noisy template sprawl.
- GUI interaction remains thinly tested; critical logic is pushed into service layer tests.

## 6. Recommended Sprint 4 direction
- Add timeline-level workflow linking searches, findings, and notes chronologically.
- Add “promote search to lead” workflow for creating structured investigation tasks from saved searches.
- Add optional provider extensibility layer (Bing/Brave) using the same structured query model.
