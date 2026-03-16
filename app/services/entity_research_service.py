import hashlib
import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app.models.case import Entity, EntityKind, Evidence, SourceReliability
from app.services.intelligence_orchestrator import (
    MultiSourceOrchestrator,
    ProviderExecutionMetric,
    ResearchEntityRequest,
    ResearchEntityResult,
    build_research_request,
)
from app.storage.intelligence_repository import IntelligenceRepository


class ReviewResultItem(BaseModel):
    item_id: str
    provider_name: str
    summary: str
    key_fields: dict[str, str] = Field(default_factory=dict)
    occurred_at: str = ""
    provenance: str = ""
    reliability_hint: SourceReliability = SourceReliability.MEDIUM
    raw_data: dict = Field(default_factory=dict)
    promoted: bool = False


class EntityResearchSession(BaseModel):
    case_id: str
    entity: Entity
    request: ResearchEntityRequest
    provider_metrics: list[ProviderExecutionMetric]
    results: list[ReviewResultItem]
    total_results: int
    promoted_results: int
    partial_failure: bool
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PromotionOutcome(BaseModel):
    created: int
    skipped_duplicates: int
    evidence_ids: list[str] = Field(default_factory=list)


class EntityResearchService:
    """Coordinates entity research and evidence promotion as a case-native workflow.

    Operational value:
    - Keeps orchestration logic in services so GUI remains review-focused.
    - Promotes reviewed results into provenance-rich evidence for auditability.
    - Prevents duplicate promotions to reduce evidence noise.
    """

    def __init__(
        self,
        orchestrator: MultiSourceOrchestrator,
        repository: IntelligenceRepository,
    ):
        self.orchestrator = orchestrator
        self.repository = repository

    async def research_entity(
        self,
        case_id: str,
        entity_value: str,
        entity_type: str | None = None,
    ) -> EntityResearchSession:
        request = self._build_request(entity_value, entity_type)
        entity = self._get_or_create_entity(case_id, request)

        research = await self.orchestrator.research_entity(request)
        promoted = self._promoted_fingerprints(case_id, entity.id)
        review_items = self._to_review_items(research, promoted)

        promoted_count = sum(1 for item in review_items if item.promoted)
        partial_failure = any(not metric.success for metric in research.providers)
        return EntityResearchSession(
            case_id=case_id,
            entity=entity,
            request=request,
            provider_metrics=research.providers,
            results=review_items,
            total_results=len(review_items),
            promoted_results=promoted_count,
            partial_failure=partial_failure,
        )

    def promote_results(
        self,
        case_id: str,
        entity_id: str,
        selected_results: list[ReviewResultItem],
        source_reliability: SourceReliability,
        analyst_note: str = "",
    ) -> PromotionOutcome:
        if not selected_results:
            return PromotionOutcome(created=0, skipped_duplicates=0)

        known = self._promoted_fingerprints(case_id, entity_id)
        created = 0
        skipped = 0
        evidence_ids: list[str] = []

        for item in selected_results:
            fingerprint = self._result_fingerprint(item.provider_name, item.raw_data)
            if fingerprint in known:
                skipped += 1
                continue

            summary = item.summary
            if analyst_note:
                summary = f"{summary} | Analyst note: {analyst_note}"

            evidence = Evidence(
                case_id=case_id,
                entity_id=entity_id,
                description=f"{item.provider_name}: {item.summary}",
                source_reliability=source_reliability,
                raw_json_data={
                    "workflow": "entity_research",
                    "provider_name": item.provider_name,
                    "result_fingerprint": fingerprint,
                    "raw": item.raw_data,
                    "normalized_fields": item.key_fields,
                    "provenance": item.provenance,
                    "occurred_at": item.occurred_at,
                    "promoted_at": datetime.now(timezone.utc).isoformat(),
                },
                normalized_summary=summary,
            )
            self.repository.create_evidence(evidence)
            known.add(fingerprint)
            created += 1
            evidence_ids.append(evidence.id)

        return PromotionOutcome(
            created=created,
            skipped_duplicates=skipped,
            evidence_ids=evidence_ids,
        )

    def _build_request(self, entity_value: str, entity_type: str | None) -> ResearchEntityRequest:
        if entity_type and entity_type in {"PHONE", "EMAIL", "IP", "USERNAME"}:
            return ResearchEntityRequest(entity_type=entity_type, entity_value=entity_value)
        return build_research_request(entity_value)

    def _get_or_create_entity(self, case_id: str, request: ResearchEntityRequest) -> Entity:
        kind = EntityKind(request.entity_type)
        existing = self.repository.list_entities(case_id)
        for entity in existing:
            if entity.kind == kind and entity.value.lower() == request.entity_value.lower():
                return entity

        entity = Entity(
            case_id=case_id,
            kind=kind,
            value=request.entity_value,
            display_name=request.entity_value,
            metadata={"source": "entity_research"},
            tags=["entity_research"],
        )
        return self.repository.create_entity(entity)

    def _to_review_items(
        self,
        research: ResearchEntityResult,
        promoted_fingerprints: set[str],
    ) -> list[ReviewResultItem]:
        items: list[ReviewResultItem] = []
        for evidence_item in research.evidence_items:
            provider = evidence_item.provider_name
            data = evidence_item.data
            key_fields = self._extract_key_fields(data)
            summary = self._build_summary(provider, data, key_fields)
            occurred_at = self._extract_timestamp(data)
            provenance = self._extract_provenance(provider, data)
            reliability = self._reliability_hint(data)
            fingerprint = self._result_fingerprint(provider, data)
            item_id = fingerprint[:12]

            items.append(
                ReviewResultItem(
                    item_id=item_id,
                    provider_name=provider,
                    summary=summary,
                    key_fields=key_fields,
                    occurred_at=occurred_at,
                    provenance=provenance,
                    reliability_hint=reliability,
                    raw_data=data,
                    promoted=fingerprint in promoted_fingerprints,
                )
            )

        return items

    def _promoted_fingerprints(self, case_id: str, entity_id: str) -> set[str]:
        fingerprints: set[str] = set()
        for evidence in self.repository.list_evidence(case_id):
            if evidence.entity_id != entity_id:
                continue
            if evidence.raw_json_data.get("workflow") != "entity_research":
                continue
            fingerprint = evidence.raw_json_data.get("result_fingerprint")
            if fingerprint:
                fingerprints.add(fingerprint)
        return fingerprints

    @staticmethod
    def _result_fingerprint(provider_name: str, payload: dict) -> str:
        body = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(f"{provider_name}:{body}".encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_key_fields(payload: dict) -> dict[str, str]:
        preferred = [
            "indicator",
            "username",
            "platform",
            "url",
            "ip",
            "asn",
            "provider",
            "confidence",
            "collection",
        ]
        fields: dict[str, str] = {}
        for key in preferred:
            if key in payload and payload[key] not in (None, ""):
                fields[key] = str(payload[key])

        if not fields:
            for key, value in payload.items():
                if value in (None, ""):
                    continue
                fields[str(key)] = str(value)
                if len(fields) >= 4:
                    break
        return fields

    @staticmethod
    def _build_summary(provider_name: str, payload: dict, key_fields: dict[str, str]) -> str:
        if "url" in payload and "platform" in payload:
            return f"{payload.get('platform')} profile reference identified"
        if "ip" in payload and "asn" in payload:
            return f"Infrastructure attribution suggests ASN {payload.get('asn')}"
        if "indicator" in payload and "collection" in payload:
            return f"Potential breach indicator found in {payload.get('collection')}"
        if key_fields:
            first = next(iter(key_fields.items()))
            return f"{provider_name} returned {first[0]}={first[1]}"
        return f"{provider_name} returned research signal"

    @staticmethod
    def _extract_timestamp(payload: dict) -> str:
        for key in ("timestamp", "created_at", "updated_at", "observed_at"):
            value = payload.get(key)
            if value:
                return str(value)
        return ""

    @staticmethod
    def _extract_provenance(provider_name: str, payload: dict) -> str:
        if payload.get("url"):
            return f"{provider_name} via {payload.get('url')}"
        return f"{provider_name} source"

    @staticmethod
    def _reliability_hint(payload: dict) -> SourceReliability:
        confidence = str(payload.get("confidence", "")).lower()
        if confidence in {"high", "verified"}:
            return SourceReliability.HIGH
        if confidence in {"medium", "moderate"}:
            return SourceReliability.MEDIUM
        if confidence in {"low", "weak"}:
            return SourceReliability.LOW
        return SourceReliability.MEDIUM
