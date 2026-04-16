# Known Issues — Codice Civico

> Questo file persiste tra sessioni. Claude lo legge a inizio sessione per evitare errori ricorrenti.
> Aggiungere OGNI errore significativo con analisi causa radice.

## Formato Entry

```
### EC-NNN: Titolo breve
- **Data**: YYYY-MM-DD
- **Sintomo**: cosa si osserva
- **Causa**: perche' e' successo
- **Fix**: cosa e' stato fatto
- **Prevenzione**: come evitarlo in futuro
- **Status**: OPEN | FIXED | WORKAROUND
```

## Issues

### EC-001: Giustizia Excel URL changed (404)
- **Data**: 2026-04-13
- **Sintomo**: download_excel() returns None, giustizia ingest fails silently
- **Causa**: Min. Giustizia moved files from `/resources/` to `/cmsresources/cms/documents/` and removed dashes from filename (`CivileFlussi2014-2024.xlsx` → `CivileFlussi20142024.xlsx`)
- **Fix**: Updated `FLUSSI_CIVILE_URL` constant, reversed try order (new URL first, legacy fallback)
- **Prevenzione**: Add a periodic health check that verifies data source URLs are still 200
- **Status**: FIXED

### EC-002: Giustizia Excel format changed (parse error)
- **Data**: 2026-04-13
- **Sintomo**: `ValueError: Missing required columns` — parser couldn't find tribunal/incoming/resolved columns
- **Causa**: New Excel format: data in sheet 'data' (not active 'Read me'), header at row 1 (not 3), new column names ('Sede' not 'Circondario', 'Definiti - totale' not 'Definiti', 'Sopravvenuti' not 'Iscritti'), granular per-materia rows (113K) instead of aggregated
- **Fix**: Auto-detect sheet ('data' > active), auto-detect header row (scan 1-10), added column aliases ('Sede', 'Definiti - totale', 'Sopravvenuti'), aggregate by (tribunal, year) in parse_excel
- **Prevenzione**: Download and parse a sample during CI/smoke test
- **Status**: FIXED

### EC-003: Ollama model not found on registry
- **Data**: 2026-04-13
- **Sintomo**: `ollama pull swap/LLaMAntino-3-ANITA-8B-Inst-DPO-ITA-GGUF` fails — model doesn't exist on Ollama
- **Causa**: Model was hallucinated or removed from Ollama registry
- **Fix**: Changed to `llama3.1` (official Meta model, 8B, good Italian support). Alternative: `VitoF/llama-3.1-8b-italian`
- **Prevenzione**: Verify model exists via `ollama.com/library/MODEL` before adding to verified-deps
- **Status**: FIXED

### EC-004: Dockerfile.backend missing README.md COPY
- **Data**: 2026-04-16
- **Sintomo**: `docker build` fails with `Readme file does not exist: README.md` at `pip install .[nlp]` step
- **Causa**: `pyproject.toml` has `readme = "README.md"` as dynamic metadata, hatchling needs the file at build time but multi-stage Dockerfile only copied `pyproject.toml` and `src/`
- **Fix**: Added `COPY README.md .` in both builder and runtime stages (commit `017cbbb`)
- **Prevenzione**: when adding new pyproject.toml dynamic fields, check COPY in Dockerfile
- **Status**: FIXED

### EC-005: web/public/ empty directory not tracked by Git
- **Data**: 2026-04-16
- **Sintomo**: Next.js `COPY --from=builder /app/public ./public` fails: `"/app/public": not found` on VPS
- **Causa**: Git does not track empty directories. `web/public/` existed locally (empty) but was absent after `git pull` on the VPS
- **Fix**: Added `web/public/.gitkeep` (commit `52261c4`)
- **Prevenzione**: `.gitkeep` in any directory referenced by a Dockerfile COPY
- **Status**: FIXED

### EC-006: Next.js standalone binds to container hostname instead of 0.0.0.0
- **Data**: 2026-04-16
- **Sintomo**: `wget http://localhost:3000` from inside container → `Connection refused`. Docker healthcheck marks frontend `unhealthy`. Caddy reverse proxy upstream unreachable.
- **Causa**: Next.js 15 standalone `server.js` defaults to hostname binding from container hostname (e.g. `83359ba97eee:3000`), not `0.0.0.0`
- **Fix**: `ENV HOSTNAME=0.0.0.0` in `web/Dockerfile` (commit `f6395f2`)
- **Prevenzione**: always set HOSTNAME when using Next.js standalone in Docker
- **Status**: FIXED

### EC-007: SPARQL `_sparql_paginated` crashes on literal `{...}` braces
- **Data**: 2026-04-16
- **Sintomo**: `KeyError: '\n  ?vot a ocd'` during any paginated SPARQL ingest (Camera votazioni, atti, interventi; Senato)
- **Causa**: `base.py:110` used `query_template.format(limit=..., offset=...)` but SPARQL queries contain literal `{WHERE}` braces that Python interprets as placeholders
- **Fix**: `str.replace("{limit}", ...).replace("{offset}", ...)` — commit `91e46ee`. Added 2 regression tests with a realistic WHERE block (`test_ingest_base.py`)
- **Prevenzione**: never use `str.format()` on template strings that may contain user-level `{` characters (SPARQL, JSON, f-string output, etc.)
- **Status**: FIXED

### EC-008: torch pulls CUDA libs on CPU-only VPS (disk exhaustion)
- **Data**: 2026-04-16
- **Sintomo**: `docker build` fails with `no space left on device` during layer export. 21 GB of images accumulating on 40 GB disk.
- **Causa**: `pip install .[nlp]` transitively installed torch default build with ~2 GB of bundled `nvidia-*` CUDA libraries. CX22 has no GPU → pure waste
- **Fix**: Install torch CPU-only from PyTorch index URL first, then `.[nlp]` picks up the lean build. Commit `0514b47`
- **Prevenzione**: for any CPU-only deploy, explicitly install torch from `https://download.pytorch.org/whl/cpu`
- **Status**: FIXED

### EC-009: ANAC `_parse_decimal` misinterprets English decimal format
- **Data**: 2026-04-17
- **Sintomo**: `asyncpg.exceptions.NumericValueOutOfRangeError: numeric field overflow` on `amount_original NUMERIC(15,2)` with value `Decimal('7493692241800001')` (7.5 quadrillion €)
- **Causa**: ANAC open-data CSVs use english convention (dot = decimal, no thousands separator). Our parser assumed Italian (dots = thousands) and stripped every dot → 100x inflation. Value `74936922.41800001` became `7493692241800001`
- **Fix**: Auto-detect decimal format based on which separator appears last. Commit `1fde064`, +2 regression tests
- **Prevenzione**: never assume numeric locale; test with both english and italian sample CSVs
- **Status**: FIXED

### EC-010: CX22 VPS had no swap → ANAC parser OOM-killed
- **Data**: 2026-04-17
- **Sintomo**: `Killed` (SIGKILL from OOM) during ANAC CSV download/parse (~200 MB compressed → pandas in memory peak ~2.5 GB)
- **Causa**: Ubuntu 24.04 cloud image on Hetzner CX22 ships without swap. 4 GB RAM minus OS/containers leaves ~2 GB free — insufficient for ANAC parser's peak.
- **Fix**: Added 4 GB swapfile `/swapfile`, persisted in `/etc/fstab`
- **Prevenzione**: check `free -h` and `swapon --show` on every new VPS BEFORE the first heavy ingest. Budget for swap in deploy-vps.sh.
- **Status**: WORKAROUND (proper fix = streaming/chunked ANAC parser — tracked in ROADMAP deferred list)

## Open (cosmetic, non-blocking)

### EC-011: HTML entities not decoded in frontend law titles
- **Data**: 2026-04-17
- **Sintomo**: `&quot;`, `&rsquo;`, `&lt;em&gt;` visible as raw text in law titles on `/leggi` and dashboard
- **Causa**: likely LegislativeAct.title stored with HTML entities from Camera SPARQL (title might come from RDF literal that already contains them); frontend renders as plain text
- **Fix**: TBD — either decode at ingest time or via a React `dangerouslySetInnerHTML` (risky) or a decoder util
- **Status**: OPEN

### EC-012: Dashboard politician count mismatch (900 vs 668 in DB)
- **Data**: 2026-04-17
- **Sintomo**: homepage stat card shows "900 Politici tracciati" but DB `SELECT COUNT(*) FROM politicians` returns 668
- **Causa**: TBD — likely `/system/stats` endpoint counts something else (memberships? legislative periods?) or caches an older value
- **Fix**: TBD — audit counter source
- **Status**: OPEN

### EC-013: `codicecivico train --model anomaly` is a stub
- **Data**: 2026-04-17
- **Sintomo**: CLI command prints "not yet implemented". No way to populate `AnomalyFlag` table after ANAC ingest.
- **Causa**: The anomaly module (`rules.py`, `ml.py`, `scorer.py`) exists and is tested, but no pipeline CLI wires it end-to-end
- **Fix**: TBD — implement `codicecivico anomaly run` that iterates Contract, applies `check_all_rules`, computes `risk_score`, inserts AnomalyFlag rows
- **Status**: OPEN (priority: after ANAC data is in)

### EC-014: Speech ingestion returns 0 rows
- **Data**: 2026-04-17
- **Sintomo**: `_ingest_interventi` in camera.py returns 0 rows. Dependency chain: no Speech → no Promise pipeline output.
- **Causa**: TBD — SPARQL query for `ocd:intervento` may need revision (legislature URI? schema change?)
- **Fix**: TBD — test QUERY_INTERVENTI directly against dati.camera.it endpoint
- **Status**: OPEN
