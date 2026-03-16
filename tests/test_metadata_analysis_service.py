from app.models.case import Finding, FindingType, Severity
from app.services.metadata_analysis_service import MetadataAnalysisService


def _make_finding(data: dict, *, title: str = "Metadata", description: str = "") -> Finding:
    return Finding(
        target_id="target-1",
        adapter_name="metadata",
        finding_type=FindingType.METADATA,
        title=title,
        description=description,
        data=data,
        severity=Severity.INFO,
        source_name="test",
    )


class TestMetadataAnalysisService:
    def test_extracts_source_identity_timeline_and_iocs(self):
        service = MetadataAnalysisService()
        findings = [
            _make_finding(
                {
                    "path": "C:/cases/intel/confidential-report.pdf",
                    "filename": "confidential-report.pdf",
                    "created": "2026-01-01T10:00:00+00:00",
                    "modified": "2026-01-02T11:00:00+00:00",
                    "author": "Alice Analyst",
                    "mime_type": "application/pdf",
                    "content_length": "1337",
                    "hidden": True,
                },
                description="References https://example.org and contact alice@example.org from 8.8.8.8",
            )
        ]

        summary = service.summarize(findings)

        assert any(signal.key == "Local Path" for signal in summary.source_summary)
        assert any(signal.key == "Author" and signal.value == "Alice Analyst" for signal in summary.identity_signals)
        assert any(signal.key == "Created" for signal in summary.timeline_signals)
        assert "https://example.org" in summary.iocs
        assert "alice@example.org" in summary.iocs
        assert "8.8.8.8" in summary.iocs
        assert any("confidential" in flag.lower() for flag in summary.risk_flags)
        assert any("hidden file" in flag.lower() for flag in summary.risk_flags)

    def test_formats_analysis_output_sections(self):
        service = MetadataAnalysisService()
        finding = _make_finding({"final_url": "https://example.com/a", "content_type": "text/html"})

        summary = service.summarize([finding])
        rendered = service.format_analysis(summary)

        assert "Source Overview:" in rendered
        assert "Technical Signals:" in rendered
        assert "Risk Flags:" in rendered
        assert "Extracted IOCs:" in rendered
