# ORACLE: Live Intelligence Copilot

> Continuously monitors public technology information, detects meaningful changes, connects them to related technologies and dependencies using a temporal knowledge graph, and generates evidence-backed impact reports.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.14-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB.svg)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-5.3+-646CFF.svg)](https://vitejs.dev)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4+-38B2AC.svg)](https://tailwindcss.com)

---

## 1. System Vision

ORACLE is **not a generic chatbot or simple RSS summarizer**. It operates as an autonomous technical intelligence copilot designed for senior software architects, engineering leads, and platform teams:

1. **Live Ingestion**: Streams real-time signals from official RSS/Atom feeds, GitHub releases, CVE bulletins (CISA/OSV), and cloud status pages (Cloudflare, AWS).
2. **Deterministic Change Detection**: Classifies signals into semantic categories (`breaking_change`, `security_vulnerability`, `outage`, `deprecation`, `major_release`) and extracts verbatim evidence citations.
3. **Temporal Knowledge Graph**: Connects libraries, cloud platforms, and packages via NetworkX, calculating multi-hop **blast radius propagation** (incoming dependents and transitive integrations) with temporal edge validity.
4. **Vector Retrieval**: Indexes events and reports with dense vector embeddings (ChromaDB + Sentence Transformers with pure-python fallback) for contextual retrieval.
5. **Provider-Agnostic LLM Engine**: Synthesizes evidence-backed impact dossiers with technical root cause breakdowns and actionable mitigation playbooks (with copyable commands and verification checks). Pluggable adapters support OpenAI, Anthropic, Ollama/local models, and deterministic testing fixtures.

---

## 2. Architecture & Modular Monolith

```
ORACLE/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entrypoint, CORS, lifespan
│   │   ├── config.py                  # Pydantic BaseSettings & env resolution
│   │   ├── schemas/                   # Pydantic domain models
│   │   │   ├── ingestion.py           # IngestionSource, RawSignal
│   │   │   ├── event.py               # IntelligenceEvent, Severity, EvidenceRef
│   │   │   ├── graph.py               # TemporalGraphNode, Edge, BlastRadius
│   │   │   └── report.py              # ImpactReport, MitigationAction
│   │   ├── ingestion/                 # Modular ingestion connectors
│   │   │   ├── base.py                # Abstract connector protocol + SHA-256
│   │   │   ├── rss.py                 # RSS & Atom feed parser
│   │   │   ├── github.py              # GitHub releases & tags monitor
│   │   │   ├── security.py            # CVE & OSV security advisories
│   │   │   ├── status.py              # Statuspage incident monitor
│   │   │   └── engine.py              # Deduplication orchestrator
│   │   ├── change_detection/          # Semantic classification & SemVer
│   │   ├── graph/                     # NetworkX temporal graph & blast radius
│   │   ├── retrieval/                 # ChromaDB & persistent vector index
│   │   ├── llm/                       # Pluggable LLM adapters (OpenAI, Anthropic, Ollama, Mock)
│   │   ├── impact/                    # Impact analysis & markdown dossier generator
│   │   ├── storage/                   # Thread-safe atomic JSON persistence (DiskStore)
│   │   └── api/                       # REST endpoints (/ingest, /events, /graph, /impact, /system)
│   ├── tests/                         # Pytest automated test suite (14 passing tests)
│   └── requirements.txt
│
└── frontend/                          # React + Vite + TypeScript + Tailwind CSS
    ├── src/
    │   ├── components/
    │   │   ├── Navbar.tsx             # System status, live sync trigger
    │   │   ├── LiveFeed.tsx           # Filterable stream of detected changes
    │   │   ├── KnowledgeGraphView.tsx # Interactive NetworkX graph visualizer
    │   │   ├── BlastRadiusModal.tsx   # Dependency explosion details
    │   │   ├── ImpactDossier.tsx      # Comprehensive evidence-backed dossier viewer
    │   │   └── SourceManager.tsx      # Ingestion feeds management
    │   ├── api/client.ts              # Typed API client
    │   ├── types/index.ts             # TypeScript definitions
    │   ├── App.tsx
    │   └── index.css                  # Cyber-observability dark theme
    ├── package.json
    └── vite.config.ts
```

---

## 3. Local Setup & Execution

### Prerequisites
- **Python**: `>= 3.10` (Tested on Python 3.14.0)
- **Node.js**: `>= 18.0` (Tested on Node v24.12.0)
- **npm**: `>= 9.0`

---

### Step 1: Environment Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

To configure external LLM providers, set `LLM_PROVIDER`:
- `LLM_PROVIDER=mock`: Built-in deterministic testing mode (zero API keys needed).
- `LLM_PROVIDER=openai`: Set `OPENAI_API_KEY=sk-...` (defaults to `gpt-4o-mini`).
- `LLM_PROVIDER=anthropic`: Set `ANTHROPIC_API_KEY=sk-ant-...` (defaults to `claude-3-5-sonnet-20240620`).
- `LLM_PROVIDER=ollama`: Set `OLLAMA_BASE_URL=http://localhost:11434` (defaults to `llama3`).

---

### Step 2: Backend Setup & Execution

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python -m venv .venv

# Activate virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Linux / macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The backend will be live at:
- **API Base**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`
- **System Health**: `http://127.0.0.1:8000/api/system/health`

---

### Step 3: Frontend Setup & Execution

In a new terminal:

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend will be live at:
- **Web App**: `http://localhost:5173`

---

### Step 4: Running Automated Tests

Run the complete backend test suite:

```bash
# From workspace root:
.\backend\.venv\Scripts\python.exe -m pytest backend/tests -v
```

All 14 tests cover:
- Health and system diagnostics
- Knowledge graph serialization and blast radius calculations
- Change detection, semver parsing, and CVE classification
- Impact analysis and markdown dossier formatting
- End-to-end FastAPI REST routes

---

## 4. Key Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/system/health` | Diagnostic status, counts, active LLM provider |
| `GET` | `/api/ingest/sources` | List all configured RSS/GitHub/Status sources |
| `POST` | `/api/ingest/sync` | Trigger on-demand sync of external intelligence feeds |
| `GET` | `/api/events` | List classified intelligence events with filters |
| `GET` | `/api/graph/snapshot` | Export knowledge graph nodes and edges for visualizer |
| `GET` | `/api/graph/blast-radius` | Compute dependency impact radius for any technology |
| `POST` | `/api/impact/analyze` | Synthesize evidence-backed impact dossier using LLM |
| `GET` | `/api/impact/reports` | Retrieve list of generated dossiers |
| `GET` | `/api/impact/reports/{id}/markdown` | Export formatted Markdown briefing |

---

## 5. Security & Provenance Principles
- **No Hardcoded Secrets**: All configuration is loaded from environment variables and `.env`.
- **Verbatim Evidence**: Every intelligence event and impact report links to ground-truth URLs with verbatim snippets and SHA-256 hashes.
- **Explicit Provenance**: Outputs clearly declare the generating LLM provider, model, latency, and test fixtures (never falsifying synthetic fixtures as live feeds).
