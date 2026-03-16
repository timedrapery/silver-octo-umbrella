import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TargetType(str, Enum):
    DOMAIN = "DOMAIN"
    USERNAME = "USERNAME"
    EMAIL = "EMAIL"
    IP = "IP"
    URL = "URL"
    ORGANIZATION = "ORGANIZATION"
    DOCUMENT = "DOCUMENT"


class FindingType(str, Enum):
    DNS = "DNS"
    CERTIFICATE = "CERTIFICATE"
    HTTP = "HTTP"
    SOCIAL = "SOCIAL"
    SUBDOMAIN = "SUBDOMAIN"
    METADATA = "METADATA"
    GENERIC = "GENERIC"


class Severity(str, Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingReviewState(str, Enum):
    NEW = "NEW"
    REVIEWED = "REVIEWED"
    FLAGGED = "FLAGGED"
    DISMISSED = "DISMISSED"


class FindingSortBy(str, Enum):
    NEWEST = "NEWEST"
    OLDEST = "OLDEST"
    SEVERITY = "SEVERITY"
    ADAPTER = "ADAPTER"
    TARGET = "TARGET"


class SearchProvider(str, Enum):
    GOOGLE = "GOOGLE"


class SearchIntent(str, Enum):
    GENERAL_DISCOVERY = "GENERAL_DISCOVERY"
    PERSON_PROFILE = "PERSON_PROFILE"
    USERNAME_FOOTPRINT = "USERNAME_FOOTPRINT"
    DOMAIN_EXPOSURE = "DOMAIN_EXPOSURE"
    DOCUMENT_DISCOVERY = "DOCUMENT_DISCOVERY"
    FILETYPE_DISCOVERY = "FILETYPE_DISCOVERY"
    EMAIL_MENTION = "EMAIL_MENTION"
    CREDENTIAL_MENTION = "CREDENTIAL_MENTION"
    INFRASTRUCTURE_REFERENCE = "INFRASTRUCTURE_REFERENCE"
    CONTACT_FOOTPRINT = "CONTACT_FOOTPRINT"


class EntityKind(str, Enum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    IP = "IP"
    USERNAME = "USERNAME"
    GENERIC = "GENERIC"


class SourceReliability(str, Enum):
    UNVERIFIED = "UNVERIFIED"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class MissionPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class WorkflowStage(str, Enum):
    INTAKE = "INTAKE"
    COLLECTION = "COLLECTION"
    REVIEW = "REVIEW"
    REPORTING = "REPORTING"
    ARCHIVE_READY = "ARCHIVE_READY"


class LeadLifecycleState(str, Enum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    CORROBORATED = "CORROBORATED"
    DEPRIORITIZED = "DEPRIORITIZED"
    CLOSED = "CLOSED"


class LeadPriority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ArtifactLinkType(str, Enum):
    LEAD = "LEAD"
    TARGET = "TARGET"
    ENTITY = "ENTITY"
    FINDING = "FINDING"
    EVIDENCE = "EVIDENCE"
    SAVED_SEARCH = "SAVED_SEARCH"
    ADAPTER_RUN = "ADAPTER_RUN"


class FindingDecisionState(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    CORRELATED = "CORRELATED"
    PROMOTED = "PROMOTED"
    NEEDS_MORE_SUPPORT = "NEEDS_MORE_SUPPORT"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    DISMISSED = "DISMISSED"
    NOT_ACTIONABLE = "NOT_ACTIONABLE"


class SupportLinkOrigin(str, Enum):
    MANUAL_CORRELATION = "MANUAL_CORRELATION"
    FINDING_PROMOTION = "FINDING_PROMOTION"
    ENTITY_RESEARCH_CORRELATION = "ENTITY_RESEARCH_CORRELATION"
    SYSTEM_INFERENCE = "SYSTEM_INFERENCE"


class EvidenceAttachmentType(str, Enum):
    SCREENSHOT = "SCREENSHOT"
    FILE = "FILE"
    IMAGE = "IMAGE"
    PUBLIC_MEDIA = "PUBLIC_MEDIA"
    URL_REFERENCE = "URL_REFERENCE"


class CaseStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class InvestigationPreset(str, Enum):
    DOMAIN_INTELLIGENCE = "DOMAIN_INTELLIGENCE"
    ORGANIZATION_FOOTPRINT = "ORGANIZATION_FOOTPRINT"
    USERNAME_INVESTIGATION = "USERNAME_INVESTIGATION"
    DOCUMENT_METADATA_AUDIT = "DOCUMENT_METADATA_AUDIT"
    INFRASTRUCTURE_MAPPING = "INFRASTRUCTURE_MAPPING"


class Target(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TargetType
    value: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    target_id: str
    adapter_name: str
    finding_type: FindingType
    title: str
    description: str
    data: dict = Field(default_factory=dict)
    severity: Severity
    source_url: str = ""
    source_name: str = ""
    adapter_run_id: Optional[str] = None
    review_state: FindingReviewState = FindingReviewState.NEW
    analyst_note: str = ""
    decision_state: FindingDecisionState = FindingDecisionState.PENDING_REVIEW
    decision_confidence: float = 0.5
    decision_rationale: str = ""
    decision_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)

    @field_validator("decision_confidence")
    @classmethod
    def validate_decision_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("Decision confidence must be between 0 and 1")
        return value


class Note(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    """Evidence is durable provenance that supports auditability and analyst trust."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    entity_id: Optional[str] = None
    finding_id: Optional[str] = None
    file_path: str = ""
    description: str = ""
    source_reliability: SourceReliability = SourceReliability.UNVERIFIED
    raw_json_data: dict = Field(default_factory=dict)
    normalized_summary: str = ""
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Entity(BaseModel):
    """Entity records anchor intelligence to a case so evidence can be traced and reused."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    kind: EntityKind
    value: str
    display_name: str = ""
    metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Entity value cannot be empty")
        return cleaned


class SavedSearch(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    target_id: Optional[str] = None
    title: str
    provider: SearchProvider = SearchProvider.GOOGLE
    intent: SearchIntent = SearchIntent.GENERAL_DISCOVERY
    query: str
    explanation: str
    tags: list[str] = Field(default_factory=list)
    analyst_note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MissionTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    completed: bool = False
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Mission task title cannot be empty")
        return cleaned


class MissionIntake(BaseModel):
    """Mission intake keeps objective and operating boundaries explicit before collection.

    Operational value:
    - Reduces analyst overwhelm by clarifying purpose and scope up front.
    - Anchors later findings and evidence to explicit mission intent.
    - Makes case progression repeatable from intake through reporting.
    """

    mission_summary: str = ""
    objectives: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    scope: str = ""
    constraints: str = ""
    legal_operational_notes: str = ""
    risk_notes: str = ""
    priority: MissionPriority = MissionPriority.MEDIUM
    intake_notes: str = ""
    tasks: list[MissionTask] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LeadProfile(BaseModel):
    """Unified lead profile used to reduce target/entity workflow fragmentation.

    Operational value:
    - Gives one durable operational record per subject of interest in a case.
    - Tracks lifecycle, confidence, and ownership for mission execution.
    - Links target and entity provenance so pivots stay case-native and auditable.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    kind: str
    canonical_value: str
    display_label: str
    lifecycle_state: LeadLifecycleState = LeadLifecycleState.NEW
    priority: LeadPriority = LeadPriority.MEDIUM
    owner: str = ""
    confidence_score: float = 0.5
    context_summary: str = ""
    blocker_note: str = ""
    why_it_matters: str = ""
    linked_target_ids: list[str] = Field(default_factory=list)
    linked_entity_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("canonical_value", "display_label")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Lead value cannot be empty")
        return cleaned

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return value


class MissionTaskLink(BaseModel):
    """Links mission checklist tasks to operational leads or concrete artifacts.

    Operational value:
    - Explains why a task exists by anchoring it to lead/artifact context.
    - Reduces guesswork when a case is blocked or stale.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    task_id: str
    artifact_type: ArtifactLinkType
    artifact_id: str
    note: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FindingEvidenceLink(BaseModel):
    """Links findings to evidence so signal-support reasoning is durable and reviewable.

    Operational value:
    - Makes it explicit what evidence supports a finding and why.
    - Preserves analyst rationale and confidence for later review/reporting.
    - Reduces ambiguity between raw signal collection and corroborated conclusions.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    finding_id: str
    evidence_id: str
    origin: SupportLinkOrigin = SupportLinkOrigin.MANUAL_CORRELATION
    support_confidence: float = 0.5
    rationale: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("support_confidence")
    @classmethod
    def validate_support_confidence(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("Support confidence must be between 0 and 1")
        return value


class EvidenceAttachment(BaseModel):
    """Attachment support records keep screenshots and public media durable and auditable.

    Operational value:
    - Integrates screenshot/file/media capture into normal evidence workflows.
    - Preserves source URL, provenance notes, and capture metadata for review.
    - Keeps support artifacts case-linked so reporting and readiness can reason on them.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    evidence_id: str
    attachment_type: EvidenceAttachmentType
    source_url: str = ""
    media_title: str = ""
    media_type: str = ""
    file_path: str = ""
    source_platform: str = ""
    provenance_note: str = ""
    metadata: dict = Field(default_factory=dict)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AdapterRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AdapterRun(BaseModel):
    """Records execution metadata for a single adapter run within an investigation."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    target_id: str
    adapter_name: str
    status: AdapterRunStatus = AdapterRunStatus.PENDING
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    finding_count: int = 0
    duration_seconds: float = 0.0
    error_message: str = ""


class Case(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    targets: list[Target] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    notes: list[Note] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    saved_searches: list[SavedSearch] = Field(default_factory=list)
    mission_intake: MissionIntake = Field(default_factory=MissionIntake)
    workflow_stage: WorkflowStage = WorkflowStage.INTAKE
    workflow_stage_note: str = ""
    workflow_stage_updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    leads: list[LeadProfile] = Field(default_factory=list)
    task_links: list[MissionTaskLink] = Field(default_factory=list)
    finding_evidence_links: list[FindingEvidenceLink] = Field(default_factory=list)
    evidence_attachments: list[EvidenceAttachment] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CaseStatus = CaseStatus.OPEN
    adapter_runs: list[AdapterRun] = Field(default_factory=list)
