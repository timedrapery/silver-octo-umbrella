# OSINT Research Platform

A powerful but accessible tool that allows analysts, investigators, journalists, researchers, and security professionals to conduct open-source intelligence research from a unified interface.

---

## Overview

The OSINT Research Platform is a desktop application built with Python and PySide6 that provides a structured, GUI-driven workbench for open-source intelligence (OSINT) investigations. It aggregates information from multiple data sources, organizes findings into cases, visualizes entity relationships, and generates exportable reports.

**Key capabilities:**
- Case-based investigation management
- Multi-source intelligence aggregation via a modular adapter system
- Interactive relationship graph visualization
- Timeline and findings explorer
- HTML, JSON, and CSV report export
- Fully offline, no API keys required (adapters use mock data by default)

---

## Installation

### Requirements

- Python 3.12+
- pip

### Steps

```bash
# Clone the repository
git clone https://github.com/timedrapery/silver-octo-umbrella.git
cd silver-octo-umbrella

# Install dependencies
pip install -r requirements.txt

# Run the application
python app/main.py
```

---

## Architecture

```
silver-octo-umbrella/
├── app/
│   ├── main.py                     # Application entry point
│   ├── gui/
│   │   ├── main_window.py          # Main application window (dark-themed QMainWindow)
│   │   ├── case_panel.py           # Case management UI
│   │   ├── findings_panel.py       # Findings explorer (table + detail view)
│   │   ├── graph_panel.py          # Relationship graph viewer (pyvis + WebEngineView)
│   │   ├── report_panel.py         # Report generation UI
│   │   ├── workers.py              # QThread workers for async investigations
│   │   └── widgets/
│   │       ├── finding_card.py     # Finding detail card widget
│   │       ├── progress_widget.py  # Progress bar + message widget
│   │       └── target_input.py     # Target type + value input widget
│   ├── core/
│   │   └── adapters/
│   │       ├── base.py             # BaseAdapter abstract class
│   │       ├── dns_adapter.py      # DNS / domain intelligence
│   │       ├── cert_adapter.py     # Certificate transparency
│   │       ├── http_adapter.py     # HTTP fingerprinting
│   │       ├── social_adapter.py   # Social account discovery
│   │       ├── subdomain_adapter.py# Subdomain enumeration
│   │       └── metadata_adapter.py # Document metadata extraction
│   ├── models/
│   │   └── case.py                 # Pydantic v2 data models
│   ├── services/
│   │   ├── case_service.py         # Case CRUD operations
│   │   ├── investigation_service.py# Adapter orchestration + presets
│   │   ├── report_service.py       # Report generation (HTML/JSON/CSV)
│   │   └── graph_service.py        # Relationship graph builder (networkx + pyvis)
│   ├── storage/
│   │   └── database.py             # SQLite storage layer
│   └── reports/
│       └── templates/
│           ├── report.html.j2      # HTML report template
│           └── report_pdf.html.j2  # PDF-optimized report template
├── tests/
│   ├── test_models.py
│   ├── test_adapters.py
│   ├── test_services.py
│   └── test_storage.py
├── requirements.txt
└── pyproject.toml
```

### Key design patterns

| Layer | Technology | Purpose |
|-------|-----------|---------|
| GUI | PySide6 | Desktop interface, dark theme |
| Models | Pydantic v2 | Validated, serializable data structures |
| Storage | SQLite (sqlite3) | Persistent case and finding storage |
| Async | asyncio + QThread | Non-blocking investigations |
| Visualization | networkx + pyvis | Interactive relationship graphs |
| Reports | Jinja2 | Templated HTML/PDF reports |

---

## How to Add New OSINT Modules

1. Create a new file in `app/core/adapters/`, e.g. `whois_adapter.py`.

2. Subclass `BaseAdapter` and implement the `run` method:

```python
import asyncio
from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType

class WhoisAdapter(BaseAdapter):
    name = "whois"
    description = "Retrieves WHOIS registration data for domain targets."
    supported_target_types = [TargetType.DOMAIN]

    async def run(self, target: Target) -> list[Finding]:
        await asyncio.sleep(1)  # Replace with real network call
        return [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.DNS,
                title=f"WHOIS: {target.value}",
                description="Registrar: Example Registrar Inc.",
                data={"registrar": "Example Registrar Inc.", "created": "2010-01-01"},
                severity=Severity.INFO,
                source_url=f"https://whois.iana.org/{target.value}",
                source_name="IANA WHOIS",
            )
        ]
```

3. Register the adapter in `app/gui/main_window.py` inside `_setup_services()`:

```python
from app.core.adapters.whois_adapter import WhoisAdapter

self.investigation_service = InvestigationService([
    DnsAdapter(), CertAdapter(), HttpAdapter(),
    SocialAdapter(), SubdomainAdapter(), MetadataAdapter(),
    WhoisAdapter(),   # ← add here
])
```

4. Add a checkbox for it in `_build_investigation_tab()`:

```python
for name in ["dns", "cert", "http", "social", "subdomain", "metadata", "whois"]:
```

---

## How to Run Investigations

1. **Start the application:**
   ```bash
   python app/main.py
   ```

2. **Create a case:** Click **+ New Case** in the left sidebar and enter a name.

3. **Open the Investigation tab.**

4. **Enter a target:**
   - Select the target type (Domain, Username, Email, IP, URL, Organization, Document)
   - Enter the target value (e.g. `example.com`)

5. **Run adapters:**
   - Click a **preset button** for a guided workflow (Domain Intel, Org Footprint, etc.)
   - Or select individual adapters using the checkboxes and click **▶ Start Investigation**

6. **View findings:** Switch to the **Findings** tab to explore all collected findings, filter by severity, and view raw data.

7. **Explore relationships:** Switch to the **Graph** tab to view an interactive entity relationship graph.

---

## How to Export Reports

1. Switch to the **Reports** tab.
2. Select the desired output format: **HTML**, **JSON**, or **CSV**.
3. Click **Export Report** and choose a save location.
4. HTML reports include an executive summary, findings table, and source citations.

---

## Investigation Presets

| Preset | Adapters Used | Best For |
|--------|--------------|----------|
| Domain Intelligence | dns, cert, http, subdomain | Domain investigation |
| Organization Footprint | dns, cert, http, subdomain, social | Company research |
| Username Investigation | social | Social media presence |
| Infrastructure Mapping | dns, cert, subdomain, http | Network mapping |
| Document Metadata Audit | metadata | Document analysis |

---

## Data Models

| Model | Fields |
|-------|--------|
| `Case` | id, name, description, targets, findings, notes, evidence, tags, status, created_at, updated_at |
| `Target` | id, type (TargetType), value, created_at, notes, tags |
| `Finding` | id, target_id, adapter_name, finding_type, title, description, data, severity, source_url, source_name, collected_at, tags |
| `Note` | id, case_id, content, created_at, tags |
| `Evidence` | id, case_id, finding_id, file_path, description, collected_at |

---

## Running Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

All tests use mock data and do not require external network access.

---

## Use Cases

- **Investigative journalism** — Research organizations, domains, and public figures
- **Cybersecurity research** — Map attack surfaces and infrastructure
- **Digital footprint analysis** — Audit your own public exposure
- **Brand monitoring** — Track mentions and domain registrations
- **Threat intelligence** — Aggregate indicators of compromise
- **Corporate due diligence** — Research counterparties
- **Academic research** — Structured data collection from public sources

---

## License

MIT

