# Status — Codice Civico

## Fase Corrente
F4 NLP Promise Tracker — COMPLETED | F3 Anomaly Detection — COMPLETED | F2 Ingestion — COMPLETED

## Ultimo Subtask Completato
ST-4.6: CLI + Tests L1-L3 (139 test verdi totali)

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

## Prossimo Subtask
F5: Justice Map (scraping statistiche ~140 tribunali + choropleth) o Legislative Translator (Ollama) — attendere direzione utente

## Blockers
- `make` non disponibile su Windows — usare comandi diretti (mypy, ruff, pytest)
- Votazioni individuali (singolo deputato->voto) richiedono query SPARQL su `ocd:voto` (57M record) — rimandato a fase successiva
- Aggiudicatari ANAC: nomi colonne esatti da confermare su primo download reale (ragione_sociale/codice_fiscale)
- 4 errori mypy pre-esistenti in stub ingestor (openpolis, giustizia, csm, assets) — firma incompatibile con BaseIngestor

## Log Sessioni
- 2026-03-23: F0 completata (ricerca + architettura). Piano approvato.
- 2026-03-23: F1 completata. 40 file Python, 15 ORM models, 18 API endpoints (incl. 3 dossier). Lint + mypy + 3 smoke test verdi.
- 2026-03-23: F2 ingestion parlamento — implementati CameraIngestor e SenatoIngestor con query SPARQL verificate live. 20 test verdi (mypy + ruff + pytest). CLI funzionante.
- 2026-03-23: F2 entity resolution + ANAC — entity resolver (4 strategie), ANAC bulk CSV ingestor, CLI entity-resolve. 47 test verdi (mypy + ruff + pytest).
- 2026-03-23: F3 anomaly detection — 7 rules, IsolationForest (7 features), composite scorer (0-100). 76 test verdi totali.
- 2026-03-23: F4 NLP Promise Tracker — sentence split, claim detection (14 patterns), topic classification (13 topic), specificity scoring, promise-legislation matching (sentence-transformers). 139 test verdi totali.

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
