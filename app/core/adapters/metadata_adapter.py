import asyncio
import random
from datetime import datetime, timedelta, timezone

from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType


class MetadataAdapter(BaseAdapter):
    name = "metadata"
    description = "Document and URL metadata extraction"
    supported_target_types = [TargetType.DOCUMENT, TargetType.URL]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(random.uniform(0.5, 2.0))

        authors = ["John Smith", "Jane Doe", "Alice Johnson", "Bob Williams", "admin", "user1"]
        software = ["Microsoft Word 16.0", "LibreOffice 7.5", "Adobe Acrobat 2023", "Google Docs"]
        companies = ["Acme Corp", "Tech Solutions Ltd", "Example Inc", "Global Systems"]

        created = datetime.now(timezone.utc) - timedelta(days=random.randint(30, 730))
        modified = created + timedelta(days=random.randint(1, 30))

        author = random.choice(authors)
        app_software = random.choice(software)
        company = random.choice(companies)

        findings_data = [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="Document Author Metadata",
                description=f"Document author identified: '{author}' from organization '{company}'",
                data={
                    "author": author,
                    "company": company,
                    "created": created.isoformat(),
                    "modified": modified.isoformat(),
                },
                severity=Severity.MEDIUM,
                source_name="Metadata Extraction",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="Creation Software Identified",
                description=f"Document created with: {app_software}",
                data={"software": app_software, "version": app_software.split()[-1]},
                severity=Severity.LOW,
                source_name="Metadata Extraction",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="GPS Coordinates in Metadata",
                description="GPS location data found embedded in document metadata",
                data={
                    "latitude": round(random.uniform(-90, 90), 6),
                    "longitude": round(random.uniform(-180, 180), 6),
                    "altitude": round(random.uniform(0, 500), 1),
                },
                severity=Severity.HIGH,
                source_name="Metadata Extraction",
            ),
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.METADATA,
                title="Revision History",
                description=f"Document has {random.randint(3, 20)} revisions tracked in metadata",
                data={"revision_count": random.randint(3, 20), "last_modified_by": author},
                severity=Severity.LOW,
                source_name="Metadata Extraction",
            ),
        ]

        count = random.randint(2, 4)
        return findings_data[:count]
