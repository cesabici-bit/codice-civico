# Status — Codice Civico

## Fase Corrente
F9 Deploy Live su VPS — IN PROGRESS | F8 Deploy Infra — COMPLETED | F7 Legislative Translator — COMPLETED | F6 Frontend + README — COMPLETED | F5 Justice Map — COMPLETED | F4 NLP Promise Tracker — COMPLETED | F3 Anomaly Detection — COMPLETED | F2 Ingestion — COMPLETED

## Ultimo Subtask Completato
ST-9.3-9.5: Deploy + migrate + verify. Applied 3 Docker fixes (README.md copy, web/public .gitkeep, Next.js HOSTNAME=0.0.0.0). All 5 containers UP. Alembic 0001 applied. /api/v1/health/detailed all OK. Frontend HTTP 200 via Caddy.

## F9 Deploy Live — Stato Dettagliato (2026-04-16)

### VPS
- Provider: Hetzner Cloud, progetto `codice-civico`, server `codice-civico-prod`
- Type: CX22 (4 GB RAM, 40 GB SSD, 3.85 EUR/mese)
- Location: Nürnberg
- OS: Ubuntu 24.04.3 LTS
- IPv4: **46.225.219.136**
- SSH: `ssh -i /c/Users/cesab/.ssh/id_ed25519 root@46.225.219.136`

### Done
- [x] ST-9.1: VPS provisioning (Hetzner CX22, Nürnberg, Ubuntu 24.04)
- [x] ST-9.2: `.env` + CORS + POSTGRES_PASSWORD
- [x] ST-9.3: Docker build (3 fixes applied — README.md in Dockerfile.backend, .gitkeep for web/public, HOSTNAME=0.0.0.0 for Next.js)
- [x] ST-9.4: `docker compose up -d` — 5 containers running
- [x] ST-9.5: `alembic upgrade head` — schema + seed 143 tribunali
- [x] Verify: `/api/v1/health/detailed` all OK, frontend HTTP 200 via Caddy

### In Progress
- [ ] ST-9.6: SKIP ollama model pull (CX22 has only 4 GB; model needs ~5 GB). Translator uses graceful fallback.

### Pending
- [ ] ST-9.7: Backup cron setup: `0 5 * * * /opt/codice-civico/scripts/backup-pg.sh`
- [ ] ST-9.8: First ingest with `ANAC_FROM_YEAR=2024 bash scripts/ingest-full.sh`
- [ ] ST-9.9: Visual verify browser `http://46.225.219.136/`

### Critical Decisions CX22
- Ollama container runs idle (~100 MB) but **model NOT pulled** — would OOM.
- To enable translation: upgrade to CX32 (8 GB) and `docker compose ... exec ollama ollama pull llama3.1`
- DO NOT re-run `deploy-vps.sh` blindly — it does `git pull --ff-only`, run individual steps instead.

## Subtask Completati F2
- ST-2.3: Base ingestor enhancements (SPARQL helper con retry/timeout/logging, pagination, ingestion log)
- ST-2.1: Camera dei Deputati SPARQL ingestor (deputati, gruppi, votazioni, atti, interventi)
- ST-2.2: Senato della Repubblica SPARQL ingestor (senatori, gruppi, votazioni, DDL)
- ST-2.4: Test L2 con oracolo esterno (17 test — fixture offline, mock SPARQL)
- ST-2.5: CLI integration (`codicecivico ingest --source camera/senato`)
- ST-2.6: Entity resolution — resolve_politician (4 strategie: tax_code_hash, name+birth, normalized, fuzzy pg_trgm) + merge_cross_chamber (dedup Camera/Senato)
- ST-2.7: ANAC ingestor — bulk CSV download (CIG + aggiudicatari), parse, join by CIG, upsert Contract
- ST-2.8: CLI updates — `ingest --source anac --year --month` + `entity-resolve` command
- ST-2.9: Tests — 9 test entity resolution (L1 normalize, L2 cross-chamber logic) + 18 test ANAC (L1 parse/map, L2 fixture/field validation)

## Subtask Completati F3 (Anomaly Detection)
- ST-3.1: 7 rule-based red flags (SPLIT_CONTRACTS, SINGLE_BID, LAST_MINUTE, PRICE_SPIKE, REVOLVING_DOOR, SHORT_DURATION, EXTENSION_ABUSE)
- ST-3.2: IsolationForest feature extraction (7 features) + training + anomaly scoring + composite risk scorer (0-100)
- ST-3.3: 29 test (L1 unit per regola, L2 ANAC patterns, ML train+predict, scorer formula)

## Subtask Completati F4 (NLP Promise Tracker)
- ST-4.1: Sentence splitting (spaCy it_core_news_lg + regex fallback) + 8 smoke test
- ST-4.2: Promise heuristic detection — 14 commitment verb patterns + future tense regex + procedural/question filters
- ST-4.3: Topic classification (13 topic keyword-based) + specificity scoring (additive heuristic 0-1)
- ST-4.4: Full pipeline (extract_promises) + DB integration (pipeline.py: run_promise_pipeline) + CLI `nlp --pipeline promises`
- ST-4.5: Promise-legislation matching (sentence-transformers MiniLM-L12 + TF-IDF fallback, cosine similarity). Added matched_act_id + match_similarity to Promise model
- ST-4.6: 63 NLP test (L1 unit per funzione, L2 con SOURCE da Camera.it/Treccani, L3 Hypothesis property-based) + 15 matcher test

## Subtask Completati F5 (Justice Map)
- ST-5.1: openpyxl dependency + tribunali_seed.py (143 tribunali, 20 regioni, coordinate)
- ST-5.2: GiustiziaIngestor — Excel download + parse (column resolution, metric computation)
- ST-5.3: Upsert CourtStat + tribunal seeding + clearance_rate/disposition_time computation
- ST-5.4: 24 test (L1 unit parse/metrics, L2 SOURCE CEPEJ/MinGiustizia/ISTAT, L3 Hypothesis property-based)
- ST-5.5: API rankings (GET /courts/rankings) + national stats (GET /courts/stats/national)
- ST-5.6: CLI `ingest --source giustizia` + full suite 163 test verdi

## Subtask Completati F6 (README + Frontend)
- ST-R.1: README professionale (da 14 righe a ~230 righe: badges, 5 features, architettura, API reference, quick start, testing, roadmap)
- ST-F6.1: Next.js 15 scaffolding (package.json, tsconfig, next.config standalone, Tailwind 4 CSS-based)
- ST-F6.2: lib/types.ts (mirror esatto di schemas.py), lib/api.ts (server-side fetch wrapper tipizzato), lib/utils.ts, lib/constants.ts
- ST-F6.3: Layout (Navbar con Cmd+K search modal, Footer, ThemeToggle dark/light)
- ST-F6.4: Dashboard homepage (hero, 4 stat cards, 4 section cards con icone, top anomalie table, ultime leggi)
- ST-F6.5: /politici (FilterBar: nome/camera/regione + DataTable) + /politici/[id] dossier (ScoreGauge coerenza, PromiseBreakdown donut, AssetTimeline bar chart, voti, appalti collegati, leggi)
- ST-F6.6: /appalti (tabella con RiskBadge) + /appalti/anomalie (card grid) + /appalti/[id] (dettaglio + AnomalyFlagList con severity)
- ST-F6.7: /giustizia (ItalyMap react-leaflet con CircleMarker + MetricSelector 5 metriche + rankings table) + /giustizia/[id] (CourtTrend line chart)
- ST-F6.8: /leggi (lista + filtri) + /leggi/[id] (traduzione AI formatted + testo integrale) + /cerca (risultati raggruppati per entity_type)
- ST-F6.9: Dockerfile multi-stage (Node 22 alpine, standalone), docker-compose.yml aggiornato con frontend service
- Build green: 11 route, 0 errori TS, First Load JS 102-210KB

## Subtask Completati F7 (Legislative Translator)
- ST-7.1: translator.py — Ollama HTTP client (httpx), _build_prompt, _parse_llm_response, split_into_articles, translate_article, translate_law, check_ollama_available. Graceful fallback when Ollama unavailable.
- ST-7.2: API endpoint POST /laws/{id}/translate — triggers translation, caches result in DB, returns 503 if Ollama down. force=true per ri-tradurre.
- ST-7.3: CLI `translate --law-id --force --max-articles` — full implementation with JSON output
- ST-7.4: 36 test (L1 unit prompt/parse/split/translate, L2 SOURCE Normattiva D.L. 34/2019, L3 Hypothesis property-based). 199 test verdi totali.

## Subtask Completati F8 (Deploy + Ingest Reale)
- ST-8.1: Dockerfile.backend multi-stage (builder + runtime, non-root appuser, no dev deps, spaCy model, healthcheck)
- ST-8.2: Alembic initial migration (15 tabelle, pg_trgm/pgvector/uuid-ossp extensions, 143 tribunali seed)
- ST-8.4: Caddyfile (reverse proxy, security headers, gzip, access log)
- ST-8.5: .env.example + config.py (log_level, scheduler_enabled default false) + .gitignore updates
- ST-8.3: docker-compose.prod.yml (5 servizi: postgres pgvector, backend, frontend, ollama, caddy; memory limits, healthchecks, log rotation)
- ST-8.6: APScheduler (6 job cron: camera/senato/entity-resolve/nlp daily, anac/giustizia monthly; integrated in app.py lifespan)
- ST-8.7: /health/detailed endpoint (DB, Ollama, disk, scheduler checks)
- ST-8.11: Rate limiting (slowapi: 60/min general, 10/min translate; shared ratelimit.py module)
- ST-8.8: scripts/ingest-full.sh (pipeline ordinata con error handling e logging)
- ST-8.9: scripts/backup-pg.sh (pg_dump compresso, retention 7 giorni)
- ST-8.10: scripts/deploy-vps.sh (Ubuntu 24.04: Docker, ufw, fail2ban, clone, build, migrate, Ollama pull, backup cron)
- ST-8.12: Pre-deploy verification — tested all 4 data sources live, fixed Giustizia URL (404), fixed Excel parser (new format), fixed Ollama model name, improved ANAC ingest (historical + 6-month window)

## Prossimo Subtask
VPS provisioning manuale (utente) → push fix → deploy → ingest dati reali → verifica

## Log Sessioni
- 2026-03-24: F7 Legislative Translator — translator.py (Ollama client + graceful fallback), API POST /laws/{id}/translate, CLI translate, 36 test (L1/L2/L3). 199 test verdi totali. mypy + ruff clean.
- 2026-03-24: F8 Deploy — All 11 subtask completati. Dockerfile multi-stage, Alembic migration (15 tabelle + seed), docker-compose.prod.yml (5 servizi), Caddyfile, APScheduler (6 job), /health/detailed, slowapi rate limiting, 3 script operativi (ingest-full, backup-pg, deploy-vps). Corretto branding da "Genius Lab" a "cesabici-bit". 199 test verdi, ruff clean.
- 2026-04-13: Pre-deploy verification. Tested all real data sources: Camera SPARQL OK (254+ deputati), Senato SPARQL OK (254 senatori), ANAC CIG OK (112K rows/mese), Giustizia Excel FIXED (URL changed from /resources/ to /cmsresources/cms/documents/, filename without dashes, new sheet/header structure). Fixed parser to auto-detect sheet ('data'), auto-detect header row, aggregate granular per-materia data by (tribunal,year). Fixed Ollama model (swap/LLaMAntino non esiste su Ollama → llama3.1). Improved ANAC ingest: 6-month window + ANAC_FROM_YEAR per historical. 199 test verdi.

## Blockers
- `make` non disponibile su Windows — usare comandi diretti (mypy, ruff, pytest)
- Votazioni individuali (singolo deputato->voto) richiedono query SPARQL su `ocd:voto` (57M record) — rimandato a fase successiva
- ANAC 2026 data non ancora pubblicati — ultimo mese disponibile: 2025-12
- 3 errori mypy pre-esistenti in stub ingestor (openpolis, csm, assets) — firma incompatibile con BaseIngestor

## Log Sessioni
- 2026-03-23: F0 completata (ricerca + architettura). Piano approvato.
- 2026-03-23: F1 completata. 40 file Python, 15 ORM models, 18 API endpoints (incl. 3 dossier). Lint + mypy + 3 smoke test verdi.
- 2026-03-23: F2 ingestion parlamento — implementati CameraIngestor e SenatoIngestor con query SPARQL verificate live. 20 test verdi (mypy + ruff + pytest). CLI funzionante.
- 2026-03-23: F2 entity resolution + ANAC — entity resolver (4 strategie), ANAC bulk CSV ingestor, CLI entity-resolve. 47 test verdi (mypy + ruff + pytest).
- 2026-03-23: F3 anomaly detection — 7 rules, IsolationForest (7 features), composite scorer (0-100). 76 test verdi totali.
- 2026-03-23: F4 NLP Promise Tracker — sentence split, claim detection (14 patterns), topic classification (13 topic), specificity scoring, promise-legislation matching (sentence-transformers). 139 test verdi totali.
- 2026-03-23: F5 Justice Map — GiustiziaIngestor (Excel parse), 143 tribunali seed, clearance rate/disposition time computation, API rankings + national stats. 163 test verdi totali.
- 2026-03-24: F6 README professionale + Frontend Next.js 15. 30+ file frontend: 11 route (italiano per SEO), Tailwind 4 dark/light, Recharts (donut/bar/line), react-leaflet (mappa Italia), Cmd+K search modal. Build green, verificato visivamente con Playwright. Dockerfile + docker-compose aggiornato.

## File Modificati F4
- src/codicecivico/nlp/ner.py: split_sentences (spaCy + regex fallback), extract_entities
- src/codicecivico/nlp/promise.py: detect_claims (14 commitment patterns), classify_topic (13 topic), score_specificity, extract_promises pipeline
- src/codicecivico/nlp/matcher.py: cosine_similarity, encode_texts (sentence-transformers + TF-IDF), find_best_matches, match_promises_to_acts (DB orchestration)
- src/codicecivico/nlp/pipeline.py: NEW — run_promise_pipeline (batch Speech processing → Promise rows)
- src/codicecivico/models.py: added matched_act_id FK + match_similarity to Promise
- src/codicecivico/cli/main.py: added `nlp --pipeline promises` command
- tests/test_nlp_smoke.py: NEW — 8 smoke test (M3)
- tests/test_nlp_promise.py: NEW — 40 test (L1 unit, L2 SOURCE, L3 Hypothesis)
- tests/test_nlp_matcher.py: NEW — 15 test (L1 cosine/encode/match, L2 semantic oracle)
- tests/fixtures/promise_samples.py: NEW — 20 hand-labeled Italian parliamentary sentences

## File Modificati F3
- src/codicecivico/anomaly/rules.py: 7 rules (SINGLE_BID, LAST_MINUTE, SHORT_DURATION, SPLIT_CONTRACTS, PRICE_SPIKE, REVOLVING_DOOR, EXTENSION_ABUSE) + check_all_rules
- src/codicecivico/anomaly/ml.py: extract_features (7 features + aggregates), train_model, predict_anomaly_scores
- src/codicecivico/anomaly/scorer.py: compute_risk_score (60% rules + 40% ML → 0-100)
- tests/test_anomaly.py: 29 test (L1 per regola, L2 ANAC patterns, ML, scorer)

## File Modificati F2
- src/codicecivico/entity/resolver.py: full implementation (resolve_politician, merge_cross_chamber, normalize_name)
- src/codicecivico/ingest/anac.py: full implementation (download ZIP, parse CSV, join CIG+aggiudicatari, upsert Contract)
- src/codicecivico/cli/main.py: added anac ingestor + entity-resolve command + --year/--month options
- tests/test_entity_resolver.py: 9 test (L1 normalize, L2 cross-chamber)
- tests/test_ingest_anac.py: 18 test (L1 parse/map, L2 fixture/domain)
- tests/fixtures/anac_cig_sample.csv: 3 contratti sample (Roma, Min. Interno, Milano)
- tests/fixtures/anac_aggiudicatari_sample.csv: 2 aggiudicatari sample
