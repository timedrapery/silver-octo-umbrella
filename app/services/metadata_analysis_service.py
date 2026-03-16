import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.models.case import Finding


@dataclass
class MetadataSignal:
    category: str
    key: str
    value: str
    confidence: str = "MEDIUM"


@dataclass
class MetadataAnalysisSummary:
    source_summary: list[MetadataSignal] = field(default_factory=list)
    identity_signals: list[MetadataSignal] = field(default_factory=list)
    timeline_signals: list[MetadataSignal] = field(default_factory=list)
    geo_signals: list[MetadataSignal] = field(default_factory=list)
    technical_signals: list[MetadataSignal] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    iocs: list[str] = field(default_factory=list)


class MetadataAnalysisService:
    _EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    _IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")

    def summarize(self, findings: list[Finding]) -> MetadataAnalysisSummary:
        summary = MetadataAnalysisSummary()
        for finding in findings:
            self._extract_source_signals(summary, finding)
            self._extract_identity_signals(summary, finding)
            self._extract_timeline_signals(summary, finding)
            self._extract_geo_signals(summary, finding)
            self._extract_technical_signals(summary, finding)
            self._extract_risk_flags(summary, finding)
            self._extract_iocs(summary, finding)

        summary.iocs = sorted(set(summary.iocs))
        summary.risk_flags = sorted(set(summary.risk_flags))
        return summary

    def _extract_source_signals(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        data = finding.data or {}
        if data.get("path"):
            summary.source_summary.append(
                MetadataSignal("SOURCE", "Local Path", str(data["path"]), confidence="HIGH")
            )
        if data.get("final_url"):
            parsed = urlparse(str(data["final_url"]))
            summary.source_summary.append(
                MetadataSignal("SOURCE", "Final URL", str(data["final_url"]), confidence="HIGH")
            )
            if parsed.netloc:
                summary.source_summary.append(
                    MetadataSignal("SOURCE", "Host", parsed.netloc, confidence="HIGH")
                )
        if data.get("filename"):
            summary.source_summary.append(
                MetadataSignal("SOURCE", "Filename", str(data["filename"]), confidence="HIGH")
            )

    def _extract_identity_signals(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        data = finding.data or {}
        identity_keys = [
            "author",
            "company",
            "owner",
            "last_modified_by",
            "creator",
            "full_name",
            "uploader",
            "channel",
        ]
        for key in identity_keys:
            value = data.get(key)
            if value:
                summary.identity_signals.append(
                    MetadataSignal("IDENTITY", key.replace("_", " ").title(), str(value), confidence="MEDIUM")
                )

        for email in self._EMAIL_PATTERN.findall(self._flatten_for_search(finding)):
            summary.identity_signals.append(
                MetadataSignal("IDENTITY", "Email", email, confidence="MEDIUM")
            )

    def _extract_timeline_signals(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        data = finding.data or {}
        timeline_keys = ["created", "modified", "last_modified", "added_date", "breach_date", "upload_date"]
        for key in timeline_keys:
            value = data.get(key)
            if value:
                summary.timeline_signals.append(
                    MetadataSignal("TIMELINE", key.replace("_", " ").title(), str(value), confidence="MEDIUM")
                )

    def _extract_geo_signals(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        data = finding.data or {}
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if latitude is not None and longitude is not None:
            summary.geo_signals.append(
                MetadataSignal("GEO", "Coordinates", f"{latitude}, {longitude}", confidence="HIGH")
            )

    def _extract_technical_signals(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        data = finding.data or {}
        technical_keys = [
            "mime_type",
            "content_type",
            "content_length",
            "etag",
            "software",
            "server",
            "platform",
            "extractor_key",
            "duration_seconds",
            "view_count",
            "like_count",
            "comment_count",
            "format_count",
        ]
        for key in technical_keys:
            value = data.get(key)
            if value not in (None, ""):
                summary.technical_signals.append(
                    MetadataSignal("TECH", key.replace("_", " ").title(), str(value), confidence="MEDIUM")
                )

    def _extract_risk_flags(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        data = finding.data or {}
        corpus = self._flatten_for_search(finding).lower()

        risky_terms = {
            "confidential": "Contains confidentiality marker",
            "internal": "Contains internal-use marker",
            "password": "Contains password-related text",
            "secret": "Contains secret-related text",
            "staging": "References staging environment",
            "backup": "References backup artifact",
        }
        for token, reason in risky_terms.items():
            if token in corpus:
                summary.risk_flags.append(reason)

        size = data.get("size_bytes")
        if isinstance(size, (int, float)) and size > 20_000_000:
            summary.risk_flags.append("Large file size may indicate archive/dump content")

        mime_type = str(data.get("mime_type", "")).lower()
        if "application/octet-stream" in mime_type:
            summary.risk_flags.append("Unknown binary file type")

        if data.get("hidden") is True:
            summary.risk_flags.append("Hidden file naming detected")

    def _extract_iocs(self, summary: MetadataAnalysisSummary, finding: Finding) -> None:
        corpus = self._flatten_for_search(finding)
        summary.iocs.extend(self._URL_PATTERN.findall(corpus))
        summary.iocs.extend(self._EMAIL_PATTERN.findall(corpus))
        for ip in self._IP_PATTERN.findall(corpus):
            if self._is_valid_ipv4(ip):
                summary.iocs.append(ip)

    @staticmethod
    def _flatten_for_search(finding: Finding) -> str:
        parts: list[str] = [finding.title, finding.description]
        try:
            parts.append(json.dumps(finding.data, default=str))
        except Exception:
            parts.append(str(finding.data))
        return "\n".join(p for p in parts if p)

    @staticmethod
    def _is_valid_ipv4(value: str) -> bool:
        parts = value.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit() or not (0 <= int(part) <= 255):
                return False
        return True

    @staticmethod
    def format_analysis(summary: MetadataAnalysisSummary) -> str:
        sections: list[tuple[str, list[str]]] = []

        def format_signals(items: list[MetadataSignal]) -> list[str]:
            return [f"- {item.key}: {item.value} [{item.confidence}]" for item in items]

        sections.append(("Source Overview", format_signals(summary.source_summary)))
        sections.append(("Identity Signals", format_signals(summary.identity_signals)))
        sections.append(("Timeline Signals", format_signals(summary.timeline_signals)))
        sections.append(("Geo Signals", format_signals(summary.geo_signals)))
        sections.append(("Technical Signals", format_signals(summary.technical_signals)))
        sections.append(("Risk Flags", [f"- {flag}" for flag in summary.risk_flags]))
        sections.append(("Extracted IOCs", [f"- {ioc}" for ioc in summary.iocs]))

        rendered: list[str] = [f"Generated: {datetime.now(timezone.utc).isoformat()}"]
        for title, lines in sections:
            rendered.append("")
            rendered.append(f"{title}:")
            if lines:
                rendered.extend(lines)
            else:
                rendered.append("- none")
        return "\n".join(rendered)
