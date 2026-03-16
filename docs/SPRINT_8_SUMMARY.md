# Sprint 8 Summary

## 1. What changed

Sprint 8 implemented Milestone 3 as a durable convergence layer across findings, evidence, and analyst reasoning.

Implemented:
- explicit finding decision model (state, confidence, rationale, timestamp)
- durable finding-evidence link model with rationale, origin, and support confidence
- durable evidence attachment model for screenshots/files/public-media URL references
- service-first convergence workflow (correlate, promote, update decision, summarize maturity)
- service-first capture workflow (attach local files, capture public-media references by URL)
- findings workspace actions for decision, correlation, and promotion
- findings workspace controls for screenshot/file attachment and URL capture
- lead workspace support-maturity visibility (correlated, unsupported, low-confidence)
- dashboard readiness/recommendations informed by convergence quality and attachment coverage
- report sections for supported findings, unresolved evidence/finding mapping gaps, and attachment/public-media context

## 2. How evidence/finding convergence works

Convergence is implemented as explicit durable links:
- one finding can link to many evidence items
- one evidence item can support many findings
- each link records:
  - case linkage
  - finding and evidence IDs
  - origin (manual correlation, finding promotion, and others)
  - support confidence
  - analyst rationale
  - created/updated timestamps

This makes support relationships queryable both directions and report-visible.

## 3. How analyst decision state and confidence work

Each finding now stores analyst decision metadata:
- decision state (`PENDING_REVIEW`, `CORRELATED`, `PROMOTED`, `NEEDS_MORE_SUPPORT`, `LOW_CONFIDENCE`, `DISMISSED`, `NOT_ACTIONABLE`)
- decision confidence (0.0 to 1.0)
- decision rationale
- decision-updated timestamp

Decision fields are persisted in storage and exposed through typed CaseService APIs.

## 4. How triage-to-evidence flow is now more structured

The workflow is now deliberate and repeatable:
1. triage and review finding
2. set decision state/confidence/rationale
3. correlate to existing evidence when support already exists
4. promote finding to new evidence when needed
5. keep link rationale and confidence durable for later review
6. attach screenshot/file/public-media support artifacts to evidence when needed

Promotion includes duplicate protection for obvious finding re-promotions and auto-creates convergence links.

URL/media capture includes practical duplicate guardrails for repeated attachment submissions.

## 5. How screenshot/attachment/public-media evidence collection fits into the workflow

Attachment and capture are integrated into evidence, not a parallel subsystem:
- local screenshot/file attachments are saved as case-linked evidence attachment records
- URL-based public-media references can create or enrich evidence in-place
- URL capture stores platform/source metadata, provenance note, and capture timestamps
- optional screenshot path can be attached during URL capture

This keeps artifacts durable, reviewable, and report-ready.

## 6. How lead workspace and dashboard benefit from convergence

Lead workspace now shows support maturity, not only volume:
- correlated finding counts
- unsupported finding counts
- low-confidence finding counts
- attachment counts and evidence items still missing attachments
- support-link context in drill-in detail

Dashboard and recommendations now include convergence gaps:
- unsupported findings
- low-confidence findings
- unlinked evidence
- evidence lacking screenshot/file/public-media support artifacts
- reporting readiness now factors in support maturity, not only artifact counts

## 7. Service/storage/model improvements

Model improvements:
- `FindingDecisionState`
- `SupportLinkOrigin`
- `FindingEvidenceLink`
- `EvidenceAttachmentType`
- `EvidenceAttachment`
- finding-level decision fields in `Finding`
- case-level `finding_evidence_links`
- case-level `evidence_attachments`

Storage improvements:
- new `finding_evidence_links` table
- new `evidence_attachments` table
- new finding decision columns in `findings`
- migration-safe backfill defaults for legacy rows
- CRUD methods for finding-evidence links, finding decisions, and evidence attachments

Service improvements:
- new `ConvergenceService` for correlation/promotion/decision APIs
- CaseService wrappers for convergence operations and summaries
- CaseService APIs for attachment association and URL-based public-media evidence capture
- lead blocker/readiness logic now uses support quality signals
- timeline includes decision, correlation, attachment, and public-media capture events

## 8. Tests added or improved

Added:
- `tests/test_convergence_service.py`
  - bidirectional support retrieval
  - finding promotion behavior
  - convergence summary counts

Updated:
- `tests/test_models.py`
  - decision defaults and link validation
- `tests/test_storage.py`
  - schema/migration checks for decision/link columns
  - decision persistence updates
  - finding-evidence link round-trip
  - evidence attachment migration and round-trip
- `tests/test_services.py`
  - case-service correlation workflow
  - promote duplicate prevention behavior
  - decision persistence behavior
  - dashboard convergence signal behavior
  - attachment and URL media capture workflow behavior
  - convergence-aware report assertions

## 9. Tradeoffs / deferred work

- Correlation remains analyst-led by design; only conservative duplicate protection is automatic.
- Confidence is intentionally lightweight (single score + state), not a full probabilistic inference system.
- Finding/evidence surface is improved without introducing a dedicated heavy correlation workbench.
- Public-media capture is URL-driven and explicit by design; no brittle platform-specific automation was added in this sprint.
- Assignment/ownership routing for decisions is deferred to avoid feature sprawl.

## 10. Recommended Sprint 9

Sprint 9 should deepen operational governance on top of convergence:
- assignment and ownership workflow for finding decisions and support gaps
- saved review queues for unsupported/low-confidence findings
- stale-support reminders and confidence trend tracking
- stronger analyst handoff and review audit ergonomics
