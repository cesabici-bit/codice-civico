# CLAUDE.md — Codice Civico

## Progetto
**Codice Civico** — AI-powered civic accountability engine for Italian politics, judiciary, and public spending

## Obiettivo
Piattaforma open-source che incrocia TUTTI i dati pubblici italiani (parlamento, appalti, giustizia, patrimoni) e produce insight actionable tramite AI: promise tracking, anomaly detection su appalti, mappa della giustizia, traduzione legislativa in linguaggio semplice. Genera **dossier auto-compilati** per ogni figura istituzionale (politici, magistrati, prefetti, dirigenti PA).

## Stack Tecnico

| Componente | Tecnologia | Versione | Motivo |
|-----------|-----------|---------|--------|
| Backend API | FastAPI | 0.115+ | genius-lab standard, async, auto OpenAPI docs |
| Database | PostgreSQL + pgvector | 16+ | FTS (pg_trgm) + vector search, no DB aggiuntivo |
| ORM | SQLAlchemy | 2.0+ | Async support, type-safe, maturo |
| Migrations | Alembic | 1.14+ | Standard per SQLAlchemy |
| NLP - NER | spaCy it_core_news_lg | 3.8+ | 86% NER italiano |
| NLP - Legal | ITALIAN-LEGAL-BERT | dbmdz | Classificazione testo legale/politico |
| NLP - Embeddings | sentence-transformers MiniLM-L12 | 4.1+ | Promise-vote matching semantico |
| NLP - Generazione | LLaMAntino-3-ANITA-8B via Ollama | latest | Traduzione legislativa locale, zero costi API |
| Anomaly ML | scikit-learn IsolationForest | 1.6+ | Standard anomaly detection |
| SPARQL | SPARQLWrapper | 2.0+ | Camera/Senato RDF endpoints |
| HTTP | httpx | 0.27+ | Async client |
| PDF | pdfplumber | 0.11+ | Parsing dichiarazioni patrimoniali |
| Scraping | BeautifulSoup4 + lxml | 4.12+ | Statistiche giustizia |
| Scheduler | APScheduler | 3.10+ | In-process cron, no Redis needed |
| Settings | pydantic-settings | 2.0+ | Config management |
| Frontend | Next.js 15 + Tailwind 4 | latest | SSR per SEO, genius-lab standard |
| Charts | Recharts | 2.15+ | React charts |
| Mappe | react-leaflet | 5.0+ | Choropleth Italia |
| Deploy | Docker Compose + Caddy | latest | VPS singolo, auto HTTPS |
| Test runner | pytest | 9.0+ | genius-lab standard |
| Type checker | mypy | 1.14+ | genius-lab standard |
| Linter | ruff | 0.9+ | genius-lab standard |
| PBT | Hypothesis | 6.100+ | Property-based testing |

> IMPORTANT: ogni dipendenza DEVE avere entry verificata in `verified-deps.toml`

## Architettura

```
Frontend (Next.js 15) — Dashboard / Search / Maps
        | REST
API Gateway (FastAPI 0.115+)
        |
+-------+-------+----------+----------+
Promise  Procurement  Justice   Legislative
Tracker  Anomaly Det  Map       Translator
        |
Entity Resolution Layer
        |
PostgreSQL 16 (pg_trgm + pgvector)
        |
Ingestion Pipeline (APScheduler)
  Camera SPARQL | Senato RDF | ANAC OCDS | Giustizia scraper
```

```
codice-civico/
├── CLAUDE.md
├── verified-deps.toml
├── KNOWN_ISSUES.md
├── STATUS.md
├── Makefile
├── pyproject.toml
├── docker-compose.yml
├── Dockerfile.backend
├── alembic.ini
├── alembic/versions/
├── src/codicecivico/
│   ├── config.py           # Settings (pydantic-settings)
│   ├── db.py               # SQLAlchemy engine + session
│   ├── models.py           # ORM models
│   ├── ingest/             # Data ingestion pipelines
│   │   ├── base.py         # BaseIngestor ABC
│   │   ├── camera.py       # Camera dei Deputati SPARQL
│   │   ├── senato.py       # Senato SPARQL
│   │   ├── openpolis.py    # Openpolis REST API
│   │   ├── anac.py         # ANAC OCDS procurement
│   │   ├── giustizia.py    # Min. Giustizia scraper
│   │   ├── csm.py          # CSM magistrate data
│   │   ├── assets.py       # Asset declaration PDFs
│   │   └── scheduler.py    # APScheduler config
│   ├── entity/             # Entity resolution
│   │   └── resolver.py     # Name matching, CF linking
│   ├── nlp/                # NLP pipelines
│   │   ├── promise.py      # Promise extraction + classification
│   │   ├── matcher.py      # Promise-vote semantic matching
│   │   ├── translator.py   # Legislative translation (Ollama)
│   │   └── ner.py          # Named entity recognition utils
│   ├── anomaly/            # Procurement anomaly detection
│   │   ├── rules.py        # Rule-based red flags
│   │   ├── ml.py           # Isolation Forest model
│   │   └── scorer.py       # Composite risk score
│   ├── api/                # FastAPI application
│   │   ├── app.py          # FastAPI app + lifespan
│   │   ├── deps.py         # Dependency injection (DB session)
│   │   ├── schemas.py      # Pydantic response models
│   │   └── routes/
│   │       ├── politicians.py
│   │       ├── magistrates.py
│   │       ├── contracts.py
│   │       ├── courts.py
│   │       ├── laws.py
│   │       ├── dossier.py   # Aggregated dossier per persona
│   │       ├── search.py
│   │       └── system.py
│   └── cli/
│       └── main.py         # click CLI: ingest, train, translate
├── tests/
│   ├── conftest.py
│   ├── test_smoke.py       # M3: E2E smoke test
│   └── ...
└── web/                    # Next.js 15 frontend (F6)
```

## Fonti Dati

| Fonte | Endpoint | Formato | Frequenza |
|-------|----------|---------|-----------|
| Camera | dati.camera.it/sparql | RDF/SPARQL | Giornaliera |
| Senato | dati.senato.it/sparql | RDF/SPARQL | Giornaliera |
| Openpolis | api3.openpolis.it | REST/JSON | Settimanale |
| ANAC | dati.anticorruzione.it | OCDS/JSON/CSV | Mensile + API real-time |
| Giustizia | datiestatistiche.giustizia.it | HTML (scraping) | Mensile |
| Patrimoni | camera.it / senato.it | PDF | Annuale |
| CSM | csm.it | HTML (scraping) | Su delibera |

## 5 Moduli Core

### 1. Promise Tracker
- spaCy sentence split -> BERT claim detection -> topic classification
- Embedding semantico (MiniLM-L12) -> match con voti via pgvector cosine similarity
- Score di coerenza per politico: (kept + pending) / total, pesato per specificita

### 2. Anomaly Detector (Appalti)
- 7 red flag rule-based: SPLIT_CONTRACTS, SINGLE_BID, LAST_MINUTE, PRICE_SPIKE, REVOLVING_DOOR, SHORT_DURATION, EXTENSION_ABUSE
- Isolation Forest su 7 feature
- Risk score composito 0-100

### 3. Justice Map
- Scraping statistiche per ~140 tribunali
- Choropleth Italia: durata media, arretrato, clearance rate

### 4. Legislative Translator
- LLaMAntino via Ollama: articolo per articolo
- Output: cosa cambia, chi beneficia, chi perde
- Fallback graceful se Ollama non disponibile

### 5. Dossier Generator
- Profilo auto-generato per ogni figura istituzionale
- **Politici**: anagrafica, coherence score, presenze, patrimonio timeline, appalti collegati, atti sponsorizzati
- **Magistrati**: performance vs media tribunale, carico lavoro, trasferimenti, disciplinari
- **Figure istituzionali**: prefetti, dirigenti PA, presidenti authority — incarichi, appalti dell'ente
- Endpoint: `/api/v1/dossier/{politician|magistrate|institutional}/{id}`
- Fonti dati: CSM (magistrati), Camera/Senato, ANAC, Min. Giustizia

## MVP Scope

### IN (MVP)
- [ ] Ingestion Camera dei Deputati (SPARQL)
- [ ] Ingestion Senato (SPARQL)
- [ ] Entity resolution politici (dedup cross-camera)
- [ ] Promise extraction da discorsi (NLP)
- [ ] Promise-vote semantic matching
- [ ] Coherence score per politico
- [ ] ANAC OCDS ingestion
- [ ] Rule-based red flags (7 regole)
- [ ] Isolation Forest anomaly detection
- [ ] Justice stats scraping + choropleth map
- [ ] Legislative translation via LLM
- [ ] REST API per tutti i moduli
- [ ] Dashboard web (Next.js)
- [ ] Docker Compose deployment

### OUT (post-MVP)
- Real-time parliamentary streaming (v0.2)
- Social media promise extraction (v0.2)
- Company registry cross-reference (v0.3)
- Multi-country support (v0.4)
- Mobile app (v0.5)

## Oracoli di Dominio

| Livello | Fonte | Uso |
|---------|-------|-----|
| L2 (sanity) | Camera.it / Senato.it sito web | Verificare dati politici ingeriti |
| L2 (sanity) | ANAC rapporto annuale | Verificare totali contratti |
| L2 (sanity) | Min. Giustizia rapporto annuale | Verificare statistiche tribunali |
| L5 (reale) | Promesse note da archivi stampa | Verificare estrazione promesse |
| L5 (reale) | Scandali appalti noti (es. CONSIP) | Verificare anomaly detection |
| L5 (reale) | Rapporto CEPEJ giustizia italiana | Cross-validare performance tribunali |

> Questi oracoli sono la base per i test L2/L5. Ogni test DEVE citare la fonte con `# SOURCE:`.

## Meccanismi Anti-Allucinazione (M1-M4)

### M1: Dependency Lock
- File: `verified-deps.toml`
- Regola: NESSUNA dipendenza nel codice senza entry verificata via web search

### M2: External Oracle Test Pattern
- Regola: ogni test file DEVE avere almeno 1 test con `# SOURCE:` da oracolo esterno
- Oracoli: Camera.it, ANAC rapporto, Min. Giustizia, CEPEJ

### M3: Smoke Before Unit
- Smoke test: avvia API -> /health risponde 200 -> ingest sample -> query API -> output leggibile
- Produce il golden snapshot (L4)

### M4: Two-Tool Verification
Non applicabile (non numerico). Cross-validation via confronto con dati pubblicati.

## Gate Specifici

### Gate Ricerca (F1)
- [x] Web search fonti dati completata
- [x] Competitor analizzati (OpenPolis, AppaltiPOP, Soldipubblici)
- [x] Oracoli L2/L5 identificati
- [x] Scope MVP approvato

### Gate Architettura (F2)
- [x] Struttura moduli definita
- [x] Schema DB progettato
- [x] API endpoints definiti
- [x] Pre-mortem completato

### Gate Implementazione (per subtask)
- [ ] `make check-all` verde
- [ ] Output ispezionabile dall'utente

### Gate Verifica (F4)
- [ ] L1: unit test path critici
- [ ] L2: almeno 3 test con `# SOURCE:`
- [ ] L3: property-based sulle invarianti core
- [ ] L4: golden snapshot revisionato dall'umano
- [ ] L5: confronto con dati reali pubblicati

## Checkpoint Utente Obbligatori
- [x] Scope MVP approvato
- [ ] Smoke test output verificato
- [ ] Golden snapshot L4 approvato
- [ ] Promise extraction verificata su politico noto
- [ ] Top 20 anomalie appalti revisionate
- [ ] Mappa giustizia verificata vs dati Min. Giustizia
- [ ] Prima del release

## Comandi

```bash
# Setup
pip install -e ".[dev]"

# Test
pytest tests/ -v

# Check completo
make check-all

# Smoke test
make smoke

# CLI
codicecivico ingest --source camera
codicecivico ingest --source anac
codicecivico train --model anomaly
codicecivico translate --law-id <id>

# Docker
docker compose up
```
