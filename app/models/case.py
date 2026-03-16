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
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)


class Note(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tags: list[str] = Field(default_factory=list)


class Evidence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    finding_id: Optional[str] = None
    file_path: str
    description: str
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
    evidence: list[Evidence] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: CaseStatus = CaseStatus.OPEN
    adapter_runs: list[AdapterRun] = Field(default_factory=list)
