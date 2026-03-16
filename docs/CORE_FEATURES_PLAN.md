# Core Features Plan

## 1. Codebase architecture assessment
- Primary language: Python.
- Framework: PySide6 desktop application with service-driven orchestration.
- Domain modeling pattern: Pydantic models in app/models/case.py.
- Storage pattern: single SQLite gateway class in app/storage/database.py with migration-safe schema checks.
- Service pattern: logic-first orchestration classes in app/services with typed outputs and test coverage.

## 2. Feature scope

### Managed Network Client
- Add a central managed outbound HTTP client for all research traffic.
- Route proxy configuration from environment variables only.
- Add user-agent rotation and randomized request jitter.
- Centralize timeout, retry policy, and HTTP 429 backoff handling.

### Multi-Source Orchestrator
- Add typed asynchronous research workflow for EMAIL, IP, USERNAME.
- Run three providers concurrently.
- Isolate provider failures to preserve partial results.
- Return structured typed result with provider metrics and evidence records.

### Intelligence Ledger (SQLite)
- Extend domain models for Entities and provenance-rich Evidence.
- Extend database schema with entities table and evidence provenance columns.
- Add migration-safe schema handling for legacy databases.
- Add repository layer CRUD for entities and evidence.

## 3. Security and reliability constraints
- No secrets, tokens, or network routing values hardcoded.
- All proxy/timeout/retry controls are environment-based.
- Network failures and rate limits must be recoverable via retry/backoff policy.
- Provenance fields must be persisted for auditability.

## 4. Test plan
- Entity and evidence model validation tests.
- Orchestrator tests for typed requests, concurrent execution, and partial failures.
- Storage tests for entities/evidence CRUD and provenance round-trips.
- Repository tests for intelligence ledger CRUD behavior.

## 5. Deliverables
- Managed network client service.
- Multi-source orchestrator and provider adapters.
- Intelligence ledger model/storage/repository enhancements.
- Unit tests for validation, orchestration, and failure tolerance.
- Summary document with implementation outcomes and tradeoffs.
