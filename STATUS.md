# Status — Codice Civico

## Fase Corrente
Sprint 2 (F10 Graph Layer) IN CORSO — **CameraIngestor rewrite F10 completato (2026-04-18)** | schema `2be6b8f` | Sprint 1 (F11) CHIUSO EC-015 | F9.5 Anomaly Calibration DEPLOYED | F8-F2 COMPLETED

**Prossimo (F10, ordine aggiornato)**:
1. ~~Ricerca ontologia Senato~~ DONE 2026-04-17 (vedi ROADMAP Sprint 2)
2. ~~Riscrivere `CameraIngestor` su `ocd:mandatoCamera`~~ DONE 2026-04-18 (ST-10.2). Vedi EC-016.
3. ~~Riscrivere `SenatoIngestor`~~ DONE 2026-04-18 (ST-10.3). Regex `senatore/(\d+)`, chamber derivato da prefisso URI mandato.
4. ~~owl:sameAs link Camera↔Senato~~ DONE 2026-04-18 (ST-10.4). `extract_sameas_camera_link` + `_link_camera_senato_sameas` attaccano `camera:{stable_id}` alla Person Senato esistente; conflitti loggati senza merge (zero-defect).
5. **ST-10.5 NEXT**: Senato party_memberships (richiede traversal blank node `adesione → gruppo → denominazione → titolo` con window matching di periodi)
6. ST-10.6: Popolamento `relationships` da dati esistenti (contract→buyer, law→sponsor, speech→speaker)
7. ST-10.7: Endpoint `/graph/{type}/{id}/expand?hops=2&as_of=YYYY-MM-DD` con CTE ricorsiva bitemporale
8. ST-10.8: Test L1/L2 (traversal 2-hop, M5 insert rejection, idempotency), poi Gate F10
9. ST-10.9: Applicare migration 0002 su VPS prod + re-run CameraIngestor + SenatoIngestor live

**Raccomandazione prossima sessione**: `/clear` prima di ST-10.5 (contesto party + blank-node traversal è distinto dal lavoro regex/SPARQL di questa sessione).

**Schema F10 (commit `2be6b8f`)**: 5 tabelle (persons, person_external_ids, mandates, party_memberships, relationships), M5 enforced (source_url NOT NULL), CK temporali, polimorfismo relationships, upgrade/downgrade verificati localmente.

**ST-10.2 CameraIngestor F10 (2026-04-18)**: `parse_camera_person_id()` estrae `(stable_id, legislature)` da URI `deputato.rdf/d\d+_\d+`. `_ingest_mandati` popola persons+person_external_ids(ns='camera')+mandates (M5: skip con warning se startDate assente). `_ingest_party_memberships` popola party_memberships con fallback a LEG_19_START se dataAdesione assente. Fixture `camera_mandati.json` costruita da live snapshot SPARQL. **245 test verdi** (+18 nuovi L1/L2). Commit `8ff768d`.

**ST-10.3 SenatoIngestor F10 (2026-04-18)**: `parse_senato_person_id()` estrae stable_id numerico da `senatore/{N}`. `_ingest_mandati_senato` popola persons+external_ids(ns='senato')+mandates. Chamber derivato da prefisso URI mandato (`S_` → senato, `C_` → camera retrospettivo); legislatura estratta sempre da mandate URI (non hardcoded a 19). M5 enforced. **256 test verdi** (+11). Commit `402a42e`.

**ST-10.4 Camera↔Senato owl:sameAs link (2026-04-18)**: `extract_sameas_camera_link()` mappa riga SPARQL → (senato_id, camera_stable_id) riusando regex Camera/Senato già verificate. `QUERY_SAMEAS_CAMERA` filtra senatori con almeno un mandato leg 19 (esistono nel DB). `_link_camera_senato_sameas` attacca `camera:{stable_id}` alla Person Senato esistente; conflitti (camera già claimato da altra Person) sono LOGGATI senza merge (zero-defect: merge entità distinte richiede review umana). Storico `dd\d+` scartato (EC-015). **265 test verdi** (+9).

## Ultimo Subtask Completato
F9.5 (2026-04-17) — Anomaly Calibration. Committed commits `0defa3d` (codice) + `9098243` (roadmap). Deployed VPS.
- PRICE_SPIKE: ratio>3x median → z-score su log(amount) per CPV-8 (z>3, min 30 samples)
- SPLIT_CONTRACTS: fix finestra 90gg reale (era bug), CPV-8 invece di CPV-5, n>=5, filtri A (diversità fornitori >=60% → suppress) + B (cluster >20 → LOW)
- Endpoint `/api/v1/stats/anomaly-calibration` + pagina `/appalti/calibrazione` per trasparenza
- 5 test L2 `test_anomaly_calibration.py` con oracoli ANAC/OECD/EU
- Risultato live: 81.947 → 24.770 flag (-70%), flag rate 48% → 11.6%, high-risk pool 968 → 332

Sprint 1 (F11 Entity Resolution) CHIUSO 2026-04-17:
- Verifica empirica: fonte terza OpenPolis (api3.openpolis.it) non risponde; codice fiscale non esposto da SPARQL Camera/Senato
- Pipeline Camera/Senato limitata a legislatura 19 → caso d'uso "cross-legislatura" strutturalmente assente nei dati attuali
- Debito tecnico registrato come EC-015 in KNOWN_ISSUES.md con trigger espliciti di rivisitazione (ingestione leg. storiche, F15 dossier)

ST-9.11-9.14 (2026-04-17): Production data-quality polish.
- ST-9.11 Aggiudicatari streaming ingest: new `AnacIngestor.update_suppliers_from_snapshot()` + CLI `anac-suppliers --snapshot YYYYMMDD`. Stream-reads 99MB CSV from within ZIP, batch UPDATE with `supplier_name IS NULL` guard. **146,860 contracts enriched with supplier info** (82% coverage). RAM stayed flat at 1.3GB.
- ST-9.12 Anomaly re-run with supplier data: **81,947 flags** (vs 81,375 before). REVOLVING_DOOR rule now fires: 572 flags (140 high, 432 medium).
- ST-9.13 `/api/v1/stats/overview` endpoint: single-query aggregates. Dashboard uses live counts (668 politicians, not hardcoded 900). New "Appalti ad alto rischio" card: 968 contracts with risk_score ≥ 70.
- ST-9.14 HTML entity decoding: `clean_text()` helper in ingest.base (html.unescape + strip inline tags). Applied to Camera/Senato ingestors for law titles and speech labels. Backfill CLI `decode-entities` ran one-shot on production: **210/250 laws cleaned**. No more `&quot;` / `&rsquo;` / `&lt;em&gt;` in UI.
- Frontend healthcheck fix: wget target from `localhost` to `127.0.0.1` (Next.js standalone binds IPv4 only, busybox resolves localhost to ::1 first). Frontend container now healthy.
- 215 tests green (+7 clean_text unit tests).

ST-9.9-9.10 (2026-04-17): ANAC full ingest + anomaly pipeline LIVE.
- Fix deployato (_parse_decimal auto-detect era in repo ma immagine VPS stale) → **170,667 contratti 2025-12** ingested in ~4min
- Raised backend memory limit 1024M→2560M (cgroup OOM at ~1GB RSS killed all prior attempts)
- Removed ollama image from VPS (10GB freed, not used on CX22)
- NEW: `anomaly/pipeline.py` (run_anomaly_pipeline) + CLI `train --model anomaly` fully implemented
- Full run scored 170,667 contracts in 80s → **81,375 AnomalyFlag rows**
  - PRICE_SPIKE: 37,527 (22%) / SPLIT_CONTRACTS: 33,494 (20%) / SHORT_DURATION: 5,594 / LAST_MINUTE: 4,760
  - SINGLE_BID + REVOLVING_DOOR = 0 (require supplier data, missing without aggiudicatari CSV)
- API `/contracts?min_risk_score=70` returns real data (top: RAI, Presidenza Consiglio, Banca d'Italia)
- 205 test verdi (+2 pipeline unit tests)

ST-9.3-9.8 (2026-04-17): MVP LIVE with partial data. 6 commits of fixes: 3 Docker (README, .gitkeep, HOSTNAME), 1 SPARQL format (str.replace not format), 1 torch CPU-only, 1 ANAC decimal format auto-detect. Backup cron + 4GB swap active.

## F9 Deploy Live — Stato Dettagliato (2026-04-16)

### VPS
- Provider: Hetzner Cloud, progetto `codice-civico`, server `codice-civico-prod`
- Type: CX22 (4 GB RAM, 40 GB SSD, 3.85 EUR/mese)
- Location: Nürnberg
- OS: Ubuntu 24.04.3 LTS
- IPv4: **46.225.219.136**
- SSH: `ssh -i /c/Users/cesab/.ssh/id_ed25519 root@46.225.219.136`

### Done (F9)
- [x] ST-9.1-9.5: VPS provisioning, .env, Docker build (3 fixes), containers up, migrate, health verify
- [x] ST-9.6: SKIP ollama model pull (4 GB RAM; graceful fallback in place)
- [x] ST-9.7: Backup cron active
- [x] Visual verify (Playwright): dashboard shows 900 politici / 144 tribunali / 5 leggi
- [x] Giustizia ingest: 1540 CourtStat records (Civile flussi 2014-2024)
- [x] F9 fix #4: SPARQL `_sparql_paginated` format bug (commit `91e46ee`, +2 tests)
- [x] F9 fix #5: torch CPU-only to fit VPS disk (commit `0514b47`)
- [x] F9 fix #6: ANAC `_parse_decimal` auto-detect format (commit `1fde064`, +2 tests)
- [x] 4 GB swap enabled on VPS (was missing, caused OOM)

### In Progress
- [ ] ST-9.8: ANAC 2025-12 ingest retry after decimal fix. Check next session:
      `ssh ... docker compose ... exec backend tail /app/data/logs/anac_v2_*.log`

### Pending (next session)
- [ ] Anomaly detection CLI/script — `train --model anomaly` is stub. Need: iterate Contract, run rules+ML+scorer, insert AnomalyFlag rows.
- [ ] HTML entity decoding bug (frontend, cosmetic): `&quot;`/`&rsquo;` visible in law titles
- [ ] Dashboard counter 900 vs 668 DB (aggregation mismatch)
- [ ] Optional: Speech ingestion (interventi SPARQL — query ok but returns 0 rows, needs review)
- [ ] Streaming ANAC parser (for multi-year ingest — current one holds full CSV in pandas memory)

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
**Sprint 2 — F10 Graph Layer con modello bitemporale**.

**Scoperta architetturale da sessione 2026-04-17**: l'ontologia `dati.camera.it` espone `ocd:mandatoCamera` con `startDate`/`endDate`/`rif_deputato`/`rif_leg` — supporta nativamente il modello a entità temporale. L'URI deputato segue il pattern `deputato.rdf/drNNNN_LL` dove `drNNNN` è persona-stabile tra legislature (verificato live: `dr3325` appare in leg. 16-22). **Nessuna deduplicazione statistica serve per i politici tra legislature: la persona è deterministicamente identificabile dal prefisso URI.**

**Implicazione F10**: ridisegnare schema in modalità bitemporale:
- Estrarre `person_id` da `drNNNN` (deterministico)
- Nodi persona stabili; mandati e appartenenze come archi con `valid_from`/`valid_to` obbligatori
- Ingestione rivolta a `ocd:mandatoCamera` (granulare nel tempo), non a `ocd:deputato` (istantaneo per legislatura)
- Tabella `relationships` con `valid_from` e `valid_to` NOT NULL come meccanismo M5 esteso

**Residuo Camera↔Senato**: verificare struttura `dati.senato.it` in apertura Sprint 2. Probabilmente identificatore persona separato → servirà link owl:sameAs o fonte terza (Wikidata Q-ID). Problema limitato al confine Camera-Senato, non diffuso.

**Gate PASS originale resta**: traversal 2-hop da politico torna azienda verificabile via source_url cliccabile + tutti primi 20 archi hanno source_url HTTP 200 + constraint M5 rigetta riga senza source_url + query "appartenenza di X al 2023-05-15" risponde deterministicamente.

Input richiesto da utente inizio prossima sessione: nessuno (design chiaro). Azione mia: aggiornare ROADMAP.md con schema bitemporale prima di iniziare implementazione.

**UPDATE 2026-04-17 (sessione successiva)**: ROADMAP.md Sprint 2 riscritto con schema bitemporale completo (`persons` + `mandates` + `party_memberships` + `relationships` con `valid_from` NOT NULL). M5 esteso a temporalità obbligatoria. Sprint 1 F11 marcato CHIUSO/DEFERRED in ROADMAP con trigger di rivisitazione. Gate F10 aggiornato con 6 criteri PASS.

**Prossima azione concreta F10** (ordine):
1. Web search + test SPARQL: esiste `osr:mandato` su `dati.senato.it` con pattern analogo a `ocd:mandatoCamera`? Qual è il pattern URI senatore?
2. Scrivere migration Alembic con le 4 tabelle nuove (politicians esistente mantenuta compat).
3. CHECKPOINT utente pre-migrate: review schema (30 min).
4. Riscrivere CameraIngestor rivolto a `ocd:mandatoCamera` + regex `dr(\d+)_\d+` per person_id deterministico.
5. Decisione utente su link Camera↔Senato (solo se identificatori separati emergono dal punto 1).

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
