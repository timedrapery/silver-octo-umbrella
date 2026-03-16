# OSINT Research Platform


A desktop OSINT workbench for solo investigators and analysts.  Built with Python 3.12+ and PySide6, it provides a structured GUI workflow for open-source intelligence investigations: create a case, add targets, run adapters, review findings, inspect relationships in a graph, and export a report.

---

## Current Status (MVP — v0.1)

The core end-to-end workflow is functional:

| Step | Status |
|------|--------|
| Create / load / delete cases | ✅ Working |
| Add targets (domain, IP, email, username, URL, document, org) | ✅ Working |
| Add analyst notes | ✅ Working |
| Run adapters (with per-adapter progress feedback) | ✅ Working |
| Deduplicated finding storage | ✅ Working |
| Findings panel with filter/sort/detail view | ✅ Working |
| Entity-based relationship graph (IP, subdomain, org, software…) | ✅ Working |
| HTML / JSON / CSV report export | ✅ Working |
| Reports include notes, entity summary, grouped findings, citations | ✅ Working |
| Adapter run log (duration, status, error) | ✅ Working |
| SQLite persistence with full round-trip reload | ✅ Working |

**All adapters are mock/offline** — they return realistic simulated data; no network calls are made and no API keys are required.

---

## Quick Start

### Requirements

- Python 3.12+

### Install

```bash
git clone https://github.com/timedrapery/silver-octo-umbrella.git
cd silver-octo-umbrella
pip install -r requirements.txt
```

### Run the application

```bash
python app/main.py
```

### Run the tests

```bash
python -m pytest tests/ -v
```

---

## Workflow

1. **Cases tab** — click *New Case* to create a case.  Select it in the sidebar.
2. **Cases tab** — add one or more targets (domain, IP, username, etc.) and optional analyst notes.
3. **Investigation tab** — set the target type/value and either choose a preset or check individual adapters, then click *▶ Start Investigation*.  If a case is active the target is automatically saved to it.
4. **Findings tab** — filter by type or severity; click a row to see the full detail panel.
5. **Graph tab** — click *Refresh Graph* to render the entity relationship graph (requires `pyvis` + `PySide6-WebEngine`).
6. **Reports tab** — choose HTML/JSON/CSV, click *Generate Report*, then *Open Report*.

---

## Architecture

```
silver-octo-umbrella/
├── app/
│   ├── main.py
│   ├── models/
│   │   └── case.py
│   ├── storage/
│   │   └── database.py
│   ├── services/
│   │   ├── case_service.py
│   │   ├── investigation_service.py
│   │   ├── normalization.py
│   │   ├── graph_service.py
│   │   └── report_service.py
│   ├── core/
│   │   └── adapters/
│   │       ├── base.py
│   │       ├── dns_adapter.py
│   │       ├── cert_adapter.py
│   │       ├── http_adapter.py
│   │       ├── social_adapter.py
│   │       ├── subdomain_adapter.py
│   │       └── metadata_adapter.py
│   ├── gui/
│   │   ├── main_window.py
│   │   ├── case_panel.py
│   │   ├── findings_panel.py
│   │   ├── graph_panel.py
│   │   ├── report_panel.py
│   │   ├── workers.py
│   │   └── widgets/
│   │       ├── finding_card.py
│   │       ├── progress_widget.py
│   │       └── target_input.py
│   └── reports/
│       └── templates/
│           └── report.html.j2
└── tests/
    ├── test_models.py
    ├── test_adapters.py
    ├── test_services.py
    └── test_storage.py
```

---

## Adapters

### Built-in adapters

| Name | Target types | Data returned |
|------|-------------|---------------|
| `dns` | DOMAIN, URL | A/AAAA/MX/NS/TXT records |
| `cert` | DOMAIN, URL | TLS cert details, SANs, historical count |
| `http` | DOMAIN, URL, IP | Server software, technologies, missing headers, path enumeration |
| `subdomain` | DOMAIN | Active subdomains with resolved IPs |
| `social` | USERNAME, EMAIL | Profile URLs across 6 platforms |
| `metadata` | DOCUMENT, URL | Author, software, GPS coords, revision history |

### Mock vs. real

All adapters are **mock-only** and safe to run offline.  The output is designed to be realistic and structurally identical to what real adapters would return.

### Adding an adapter

1. Create `app/core/adapters/my_adapter.py` inheriting from `BaseAdapter`.
2. Set `name`, `description`, and `supported_target_types`.
3. Implement `async def run(self, target: Target) -> list[Finding]`.
4. Register it in `MainWindow._setup_services()` and add a checkbox in `_build_investigation_tab()`.
5. Optionally add it to relevant `PRESET_ADAPTERS` entries in `investigation_service.py`.

```python
from app.core.adapters.base import BaseAdapter
from app.models.case import Finding, FindingType, Severity, Target, TargetType

class MyAdapter(BaseAdapter):
    name = "myadapter"
    description = "Does something useful"
    supported_target_types = [TargetType.DOMAIN]

    async def run(self, target: Target) -> list[Finding]:
        return [
            Finding(
                target_id=target.id,
                adapter_name=self.name,
                finding_type=FindingType.GENERIC,
                title="Example finding",
                description="...",
                severity=Severity.INFO,
            )
        ]
```

---

## Investigation Presets

| Preset | Adapters |
|--------|---------|
| Domain Intelligence | dns, cert, http, subdomain |
| Org Footprint | dns, cert, http, subdomain, social |
| Username Investigation | social |
| Document Metadata Audit | metadata |
| Infrastructure Mapping | dns, http, subdomain |

---

## Data Model Highlights

### Finding deduplication

A finding is considered a duplicate if another finding in the same case shares the same `(adapter_name, finding_type, title)`.  Duplicates are silently skipped.  Running an investigation twice against the same case is safe.

### Entity extraction (`app/services/normalization.py`)

Raw `Finding.data` dicts are parsed into typed entities used by the graph and HTML report:

- **ip** — DNS A/AAAA records and subdomain resolver results
- **subdomain** — cert SANs and subdomain enumeration
- **domain** — MX/NS records
- **organization** — cert issuers and document metadata
- **software** — HTTP server/technology detection
- **person** — document author metadata
- **platform** — social profile discovery

---

## Graph Visualization

Requires `pyvis` (in requirements) and `PySide6-WebEngine`:

```bash
pip install PySide6-WebEngine
```

If either package is missing the graph panel shows a safe fallback message.

---

## What is mock / what is real

| Component | Status |
|-----------|--------|
| GUI, storage, services, workflow | Real — fully functional |
| All 6 adapters | Mock — offline, realistic simulated data |

---

## What to build next

- Real network-backed DNS (via `dnspython`)
- Real cert transparency via `crt.sh` API
- Real HTTP fingerprinting via `httpx` response headers
- Real subdomain enumeration (DNS brute-force or third-party)
- Timeline view ordered by `collected_at`
- PDF report export
- Multi-target investigation (run all case targets in one click)
- Case import/export (JSON)

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

