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
