<p align="center">
  <h1 align="center">Codice Civico</h1>
  <p align="center">
    <strong>AI-powered civic accountability engine for Italian politics, judiciary, and public spending</strong>
  </p>
  <p align="center">
    <a href="#features">Features</a> &middot;
    <a href="#architecture">Architecture</a> &middot;
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#api-reference">API</a> &middot;
    <a href="#data-sources">Data Sources</a> &middot;
    <a href="#contributing">Contributing</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
    <img src="https://img.shields.io/badge/tests-163%20passing-brightgreen" alt="163 tests passing">
    <img src="https://img.shields.io/badge/FastAPI-0.115-009688" alt="FastAPI">
    <img src="https://img.shields.io/badge/PostgreSQL-16-336791" alt="PostgreSQL 16">
  </p>
</p>

---

**Codice Civico** cross-references all Italian public institutional data and produces actionable insights through AI: it tracks political promises against actual votes, detects anomalies in public procurement, maps justice system performance across 143 courts, and translates legalese into plain language. It generates **auto-compiled dossiers** for every institutional figure — politicians, magistrates, prefects, PA directors.

> **Why this exists.** Italy publishes enormous amounts of institutional data — parliamentary proceedings, procurement records, court statistics — but spread across dozens of incompatible formats and portals. No citizen, journalist, or researcher can realistically cross-reference them. Codice Civico does it automatically.

## Features

### Promise Tracker

Extracts political commitments from parliamentary speeches using NLP (14 commitment verb patterns + future tense detection), classifies them by topic (13 categories), scores their specificity, and matches them against actual legislative votes using semantic similarity (sentence-transformers MiniLM-L12).

**Output:** coherence score per politician = (kept + pending) / total, weighted by specificity.

### Procurement Anomaly Detector

Ingests ANAC (National Anti-Corruption Authority) open data and applies a dual detection system:

- **7 rule-based red flags:** split contracts, single bids, last-minute awards, price spikes, revolving doors, suspiciously short durations, extension abuse
- **IsolationForest ML model** trained on 7 extracted features

**Output:** composite risk score 0-100 per contract (60% rules + 40% ML).

### Justice Map

Scrapes Ministry of Justice statistics for 143 Italian courts (tribunali ordinari). Computes clearance rate and disposition time per court and period, enabling regional comparison.

**Output:** rankings and national aggregates via API, ready for choropleth visualization.

### Legislative Translator

Translates legislative text article-by-article into plain Italian using LLaMAntino-3 via Ollama, with graceful fallback when the LLM is unavailable.

**Output:** structured JSON — what changes, who benefits, who loses.

### Dossier Generator

Auto-compiled profile for any institutional figure, aggregating data from all modules:

| Dossier type | Contents |
|---|---|
| **Politician** | Coherence score, attendance rate, promise breakdown, recent votes, asset timeline, linked procurement contracts, sponsored legislation |
| **Magistrate** | Performance vs tribunal average, caseload, clearance rate, transfer history, disciplinary records |
| **Institutional** | Role history, linked procurement contracts by institution, tenure |

## Architecture

```
Frontend (Next.js 15) — Dashboard / Search / Maps
        | REST
API Gateway (FastAPI 0.115+)
        |
+-------+-------+----------+----------+
Promise  Procurement  Justice   Legislative
Tracker  Anomaly Det  Map       Translator
        |
Entity Resolution Layer (4 strategies)
        |
PostgreSQL 16 (pg_trgm + pgvector)
        |
Ingestion Pipeline (APScheduler)
  Camera SPARQL | Senato RDF | ANAC CSV | Min. Giustizia Excel
```

**15 ORM models** — Politicians, LegislativeActs, Votes, Speeches, Promises, Contracts, AnomalyFlags, Tribunals, Magistrates, MagistrateStats, CourtStats, AssetDeclarations, EntityLinks, InstitutionalFigures, IngestionLog.

**Entity resolution** across Camera and Senato uses 4 strategies: tax code hash, name + birth date, normalized name matching, and fuzzy pg_trgm similarity — ensuring a single unified record per person across data sources.

## Data Sources

| Source | Endpoint | Format | Frequency |
|---|---|---|---|
| Camera dei Deputati | `dati.camera.it/sparql` | RDF/SPARQL | Daily |
| Senato della Repubblica | `dati.senato.it/sparql` | RDF/SPARQL | Daily |
| ANAC | `dati.anticorruzione.it` | CSV bulk | Monthly |
| Min. Giustizia | `datiestatistiche.giustizia.it` | Excel | Monthly |
| CSM | `csm.it` | HTML scraping | On deliberation |
| Asset declarations | `camera.it` / `senato.it` | PDF | Annual |

## API Reference

18 endpoints under `/api/v1`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/stats` | System statistics |
| `GET` | `/politicians` | List/search politicians |
| `GET` | `/politicians/{id}` | Politician detail |
| `GET` | `/politicians/{id}/promises` | Promises for politician |
| `GET` | `/politicians/{id}/votes` | Vote history |
| `GET` | `/contracts` | List/search contracts |
| `GET` | `/contracts/{id}` | Contract detail with anomaly flags |
| `GET` | `/contracts/top-risk` | Highest risk score contracts |
| `GET` | `/courts` | List tribunals |
| `GET` | `/courts/rankings` | Court rankings by metric |
| `GET` | `/courts/stats/national` | National aggregates |
| `GET` | `/laws` | List/search legislative acts |
| `GET` | `/laws/{id}` | Law detail with plain translation |
| `GET` | `/magistrates` | List/search magistrates |
| `GET` | `/dossier/politician/{id}` | Full politician dossier |
| `GET` | `/dossier/magistrate/{id}` | Full magistrate dossier |
| `GET` | `/dossier/institutional/{id}` | Full institutional figure dossier |
| `GET` | `/search` | Full-text search across all entities |

Interactive API docs available at `/docs` (Swagger UI) and `/redoc` when the server is running.

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ with `pg_trgm` and `pgvector` extensions
- (Optional) [Ollama](https://ollama.ai) for legislative translation

### With Docker (recommended)

```bash
git clone https://github.com/cesabici-bit/codice-civico.git
cd codice-civico
docker compose up
```

The API will be available at `http://localhost:8000`. PostgreSQL runs on port 5432.

### Local development

```bash
# Install with all dependencies
pip install -e ".[dev,nlp]"

# Download spaCy Italian model
python -m spacy download it_core_news_lg

# Set database URL
export CC_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/codicecivico"

# Run migrations
alembic upgrade head

# Start the API server
uvicorn codicecivico.api.app:app --reload

# Run tests (163 passing)
pytest tests/ -v
```

### CLI

```bash
# Ingest parliamentary data
codicecivico ingest --source camera
codicecivico ingest --source senato
codicecivico ingest --source anac --year 2025 --month 1
codicecivico ingest --source giustizia

# Cross-chamber entity resolution
codicecivico entity-resolve

# Extract promises from speeches
codicecivico nlp --pipeline promises

# Translate a law (requires Ollama)
codicecivico translate --law-id <uuid>
```

## Testing

163 tests across 5 verification levels:

| Level | What | Count |
|---|---|---|
| **L1** Unit | Every function does what it should | Core coverage |
| **L2** Domain | Values validated against external sources (Camera.it, ANAC reports, CEPEJ, Min. Giustizia) | 20+ with `# SOURCE:` citation |
| **L3** Property | Invariants hold for any valid input (Hypothesis) | Statistical properties |
| **L4** Snapshot | Pipeline output saved and diffed — human review on change | Golden files |
| **L5** Validation | Cross-check against real published data | Case studies |

```bash
# Full test suite
pytest tests/ -v

# Type checking
mypy src/codicecivico

# Linting
ruff check src/ tests/
```

## Project Structure

```
codice-civico/
├── src/codicecivico/
│   ├── api/                 # FastAPI app + 8 route modules
│   │   ├── app.py           # Application factory + CORS + lifespan
│   │   ├── deps.py          # Dependency injection
│   │   ├── schemas.py       # Pydantic response models
│   │   └── routes/          # politicians, contracts, courts, laws,
│   │                        # magistrates, dossier, search, system
│   ├── ingest/              # Data ingestion pipelines
│   │   ├── base.py          # BaseIngestor ABC
│   │   ├── camera.py        # Camera dei Deputati (SPARQL)
│   │   ├── senato.py        # Senato della Repubblica (SPARQL)
│   │   ├── anac.py          # ANAC procurement (CSV bulk)
│   │   └── giustizia.py     # Min. Giustizia (Excel)
│   ├── entity/              # Entity resolution (4 strategies)
│   ├── nlp/                 # NLP pipelines
│   │   ├── promise.py       # Promise extraction + classification
│   │   ├── matcher.py       # Semantic matching (sentence-transformers)
│   │   ├── translator.py    # Legislative translation (Ollama)
│   │   └── ner.py           # Sentence splitting + NER
│   ├── anomaly/             # Procurement anomaly detection
│   │   ├── rules.py         # 7 rule-based red flags
│   │   ├── ml.py            # IsolationForest model
│   │   └── scorer.py        # Composite risk score (0-100)
│   ├── cli/main.py          # Click CLI
│   ├── models.py            # 15 SQLAlchemy ORM models
│   ├── config.py            # pydantic-settings
│   └── db.py                # Async engine + session
├── tests/                   # 163 tests (L1-L5)
├── alembic/                 # Database migrations
├── verify/                  # Smoke test scripts
├── docker-compose.yml       # PostgreSQL + backend
└── Dockerfile.backend
```

## Tech Stack

| Component | Technology |
|---|---|
| API | FastAPI 0.115+ (async) |
| Database | PostgreSQL 16 + pgvector + pg_trgm |
| ORM | SQLAlchemy 2.0 (async) |
| NLP | spaCy (it_core_news_lg) + sentence-transformers (MiniLM-L12) |
| ML | scikit-learn IsolationForest |
| LLM | LLaMAntino-3 via Ollama (local, zero API costs) |
| Parliament data | SPARQLWrapper (Camera/Senato RDF) |
| Procurement | ANAC bulk CSV (OCDS standard) |
| CLI | Click |
| Frontend | Next.js 15 + Tailwind CSS 4 + Recharts + react-leaflet |
| Deploy | Docker Compose + Caddy (auto HTTPS) |

## Roadmap

- [x] Backend foundation (15 models, 18 endpoints)
- [x] Parliamentary data ingestion (Camera + Senato SPARQL)
- [x] ANAC procurement ingestion
- [x] Cross-chamber entity resolution
- [x] Anomaly detection (rules + ML)
- [x] NLP promise tracker (extraction + semantic matching)
- [x] Justice map (143 courts, rankings, national stats)
- [ ] Frontend dashboard (Next.js 15)
- [ ] Legislative translator (Ollama/LLaMAntino)
- [ ] Live data ingestion + VPS deployment
- [ ] Real-time parliamentary streaming
- [ ] Social media promise extraction

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change.

```bash
# Setup dev environment
pip install -e ".[dev,nlp]"

# Run all checks before submitting
pytest tests/ -v && mypy src/codicecivico && ruff check src/ tests/
```

## License

[MIT](LICENSE)

---

<p align="center">
  Built by <a href="https://github.com/cesabici-bit">cesabici-bit</a>
</p>
