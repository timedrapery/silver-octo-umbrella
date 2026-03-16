import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models.case import Case
from app.services.normalization import extract_case_summary


class ReportService:
    def __init__(self):
        templates_dir = Path(__file__).parent.parent / "reports" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=select_autoescape(["html", "j2"]),
        )

    def generate_html(self, case: Case, output_path: str) -> None:
        template = self.env.get_template("report.html.j2")
        html = template.render(
            case=case,
            entities=extract_case_summary(case),
            now=datetime.now(timezone.utc),
        )
        Path(output_path).write_text(html, encoding="utf-8")

    def generate_json(self, case: Case, output_path: str) -> None:
        data = case.model_dump(mode="json")
        Path(output_path).write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def generate_csv(self, case: Case, output_path: str) -> None:
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "id", "title", "finding_type", "severity",
                    "adapter_name", "description", "source_url", "collected_at",
                ],
            )
            writer.writeheader()
            for finding in case.findings:
                writer.writerow(
                    {
                        "id": finding.id,
                        "title": finding.title,
                        "finding_type": finding.finding_type.value,
                        "severity": finding.severity.value,
                        "adapter_name": finding.adapter_name,
                        "description": finding.description,
                        "source_url": finding.source_url,
                        "collected_at": finding.collected_at.isoformat(),
                    }
                )
