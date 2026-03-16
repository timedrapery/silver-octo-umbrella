# Sprint 3 Summary

## 1. What changed
- Added guided search domain models to support durable case-linked search workflows:
  - `SearchProvider`
  - `SearchIntent`
  - `SavedSearch`
- Extended case model to include persisted saved searches.
- Extended SQLite storage with `saved_searches` table and full lifecycle support:
  - insert/update by ID
  - list-by-case retrieval
  - delete-by-case and delete-by-ID
  - load-case hydration integration
- Added search lifecycle methods to case service:
  - create
  - update
  - list
  - delete
  - case-level search activity summary
- Added `search_builder_service` with:
  - structured request/result models
  - guided recipe catalog
  - query construction for Google operators
  - explanation string generation
  - launch URL generation
- Added a dedicated Search Builder GUI workspace with:
  - recipe selection
  - intent and target linkage
  - structured query inputs (terms, exclusions, `site:`, `filetype:`, `intitle:`, `inurl:`)
  - query + explanation preview
  - launch/copy/save actions
  - saved-search list with load/duplicate/delete actions
- Integrated the new Search Builder tab into the main window case lifecycle.
- Added search activity metrics to case details.
- Added guided search activity section to HTML report.

## 2. Why this is materially better
Sprint 3 turns advanced query construction into a guided workflow instead of a syntax memorization task. Analysts can build high-quality Google queries using intent-focused controls, understand why each query works through generated explanations, and preserve institutional knowledge as reusable saved searches linked to cases.

## 3. User-facing workflow improvements
- Analysts can build complex Google queries without manually remembering operator syntax.
- Query recipes accelerate common workflows for profile discovery, domain exposure, document discovery, and credential mention searches.
- Generated explanation text improves trust and onboarding for less technical users.
- Browser handoff remains human-in-the-loop by opening the system browser to the generated search URL.
- Saved searches can be revisited, duplicated, refined, and reused throughout the case lifecycle.
- Case details now show guided search activity volume and recency.
- Reports now include guided search rationale and query context for downstream consumers.

## 4. Service/storage/model improvements
- Model layer now supports explicit search intent/provider semantics and durable saved-search records.
- Storage layer now persists saved searches and reloads them directly into case aggregates.
- Case service now owns search lifecycle orchestration and summary metrics.
- Search builder logic is isolated in a dedicated service to keep UI code thin and testable.

## 5. Tests added or updated
- Model tests added for saved-search defaults and search enum coverage.
- Storage tests added for:
  - `saved_searches` table presence
  - saved-search round-trip persistence
  - list-by-case retrieval
  - case delete cascade cleanup for saved searches
- Service tests added for:
  - saved-search create/update/list/delete lifecycle via case service
  - case-level search activity summary
- New service test module added for search builder behavior:
  - recipe catalog retrieval
  - term parsing and normalization
  - structured operator query generation
  - empty-input validation
  - non-Google provider rejection
- Report service test updated to assert guided-search section content in HTML output.

## 6. Tradeoffs / deferred work
- Search provider support is intentionally limited to Google for Sprint 3.
- No execution history or run-log model for browser search launches yet.
- No per-search version history or audit timeline yet.
- GUI-level interaction tests remain indirect; core behavior is validated at service/storage/model layers.

## 7. Recommended next sprint
- Add multi-provider support abstraction (for example Bing and Brave) while preserving guided intent UX.
- Add saved-search run history (timestamped launch events and optional analyst outcomes).
- Add saved-search tagging/filtering/pinning in the Search Builder list for larger investigations.
- Add report export options to include only selected search artifacts for executive vs analyst audiences.
