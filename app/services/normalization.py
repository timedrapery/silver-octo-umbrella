"""
Normalization layer that converts raw adapter findings into structured entities
and relationships for use in graphs, reports, and deduplication.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models.case import Case, Finding, FindingType


@dataclass
class Entity:
    """A discrete, typed node extracted from one or more findings."""

    entity_type: str  # ip | domain | subdomain | organization | software | person | platform
    value: str
    label: str = ""
    source_finding_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.label:
            self.label = self.value

    @property
    def node_id(self) -> str:
        return f"{self.entity_type}:{self.value}"


@dataclass
class Relationship:
    """A directed edge between two entity nodes."""

    source_id: str
    target_id: str
    rel_type: str   # resolves_to | has_san | issued_by | runs | found_on | authored_by
    label: str = ""


def extract_entities(finding: Finding) -> list[Entity]:
    """Return all typed entities that can be extracted from a single finding."""
    entities: list[Entity] = []
    ftype = finding.finding_type
    data = finding.data
    fid = finding.id

    if ftype == FindingType.DNS:
        record_type = data.get("record_type", "")
        value = data.get("value")
        if record_type in ("A", "AAAA") and isinstance(value, str):
            entities.append(Entity("ip", value, source_finding_ids=[fid]))
        elif record_type == "MX" and isinstance(value, str):
            entities.append(Entity("domain", value, label=f"MX: {value}", source_finding_ids=[fid]))
        elif record_type == "NS" and isinstance(value, list):
            for ns in value:
                entities.append(Entity("domain", str(ns), label=f"NS: {ns}", source_finding_ids=[fid]))

    elif ftype == FindingType.CERTIFICATE:
        sans: list = data.get("sans", [])
        for san in sans:
            entities.append(Entity("subdomain", str(san), source_finding_ids=[fid]))
        issuer = data.get("issuer")
        if issuer:
            entities.append(
                Entity("organization", str(issuer), label=f"CA: {issuer}", source_finding_ids=[fid])
            )

    elif ftype == FindingType.SUBDOMAIN:
        sub = data.get("subdomain")
        if sub:
            entities.append(Entity("subdomain", str(sub), source_finding_ids=[fid]))
        ip = data.get("ip")
        if ip:
            entities.append(Entity("ip", str(ip), source_finding_ids=[fid]))

    elif ftype == FindingType.HTTP:
        server = data.get("server")
        if server:
            entities.append(
                Entity("software", str(server), label=f"Server: {server}", source_finding_ids=[fid])
            )
        for tech in data.get("technologies", []):
            entities.append(Entity("software", str(tech), label=f"Tech: {tech}", source_finding_ids=[fid]))

    elif ftype == FindingType.SOCIAL:
        platform = data.get("platform")
        if platform:
            entities.append(Entity("platform", str(platform), source_finding_ids=[fid]))

    elif ftype == FindingType.METADATA:
        author = data.get("author")
        if author:
            entities.append(
                Entity("person", str(author), label=f"Author: {author}", source_finding_ids=[fid])
            )
        company = data.get("company")
        if company:
            entities.append(Entity("organization", str(company), source_finding_ids=[fid]))
        software = data.get("software")
        if software:
            entities.append(Entity("software", str(software), source_finding_ids=[fid]))

    return entities


def build_entity_map(case: Case) -> dict[str, Entity]:
    """
    Aggregate all entities across every finding in a case into a deduplicated
    map keyed by node_id.  Source finding IDs are merged across duplicates.
    """
    merged: dict[str, Entity] = {}
    for finding in case.findings:
        for entity in extract_entities(finding):
            if entity.node_id in merged:
                existing = merged[entity.node_id]
                for fid in entity.source_finding_ids:
                    if fid not in existing.source_finding_ids:
                        existing.source_finding_ids.append(fid)
            else:
                merged[entity.node_id] = entity
    return merged


def extract_case_summary(case: Case) -> dict:
    """
    Return a plain-Python dict that summarises the notable entities discovered
    in a case.  Used by the report template.
    """
    entities = build_entity_map(case).values()

    result: dict[str, list[str]] = {
        "ips": [],
        "subdomains": [],
        "domains": [],
        "organizations": [],
        "platforms": [],
        "software": [],
        "persons": [],
    }

    for e in entities:
        if e.entity_type == "ip":
            result["ips"].append(e.value)
        elif e.entity_type == "subdomain":
            result["subdomains"].append(e.value)
        elif e.entity_type == "domain":
            result["domains"].append(e.value)
        elif e.entity_type == "organization":
            result["organizations"].append(e.value)
        elif e.entity_type == "platform":
            result["platforms"].append(e.value)
        elif e.entity_type == "software":
            result["software"].append(e.value)
        elif e.entity_type == "person":
            result["persons"].append(e.value)

    # Sort and deduplicate each list
    for key in result:
        result[key] = sorted(set(result[key]))

    return result
