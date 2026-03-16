# Core Features Summary

## 1. What was implemented

### Managed Network Client
- Added app/services/managed_network_client.py.
- Centralized outbound request management with:
  - environment-driven SOCKS5/HTTP proxy support
  - randomized user-agent rotation
  - request jitter between configurable bounds (default 0.5s to 3.0s)
  - centralized timeout and retry controls
  - HTTP 429 handling with Retry-After backoff support

### Multi-Source Orchestrator
- Added app/services/intelligence_orchestrator.py.
- Added typed Pydantic request/response models for research workflow.
- Implemented asynchronous research_entity flow that runs three providers concurrently.
- Provider failures are captured in per-provider metrics without aborting the full collection.
- Result includes provider name, duration, success status, and result count.

### Intelligence Ledger (SQLite)
- Extended models in app/models/case.py with:
  - Entity model and EntityKind enum
  - SourceReliability enum
  - Evidence provenance fields: source_reliability, raw_json_data, normalized_summary, entity_id
  - Case.entities collection
- Extended app/storage/database.py:
  - new entities table
  - evidence schema enhancements and migration-safe column additions
  - CRUD helpers for entities and evidence
  - case hydration now includes entities and provenance-rich evidence
- Added repository layer app/storage/intelligence_repository.py for entity/evidence CRUD.

## 2. Intelligence value delivered
- Managed attribution controls are centralized and configurable at runtime.
- Collection reliability improves via unified retry, timeout, and rate-limit logic.
- Multi-source collection remains resilient under partial provider failures.
- Provenance-rich evidence improves auditability, explainability, and downstream analyst trust.

## 3. Tests added
- tests/test_intelligence_orchestrator.py
  - request type inference and validation
  - concurrent provider execution
  - partial failure handling
- tests/test_intelligence_repository.py
  - repository CRUD for entities and evidence
- tests/test_models.py
  - entity value validation
  - provenance defaults on evidence
- tests/test_storage.py
  - entities table validation
  - entity/evidence persistence and delete flows

## 4. Notes and tradeoffs
- Provider adapters currently support environment-configured endpoints, with deterministic mock fallbacks for offline/test reliability.
- ManagedNetworkClient is available as the centralized network layer and can be reused by additional adapters and workflows.
- Evidence/file path behavior remains backward-compatible to avoid breaking existing flows while adding provenance fields.
