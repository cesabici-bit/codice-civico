# Roadmap — Codice Civico

> **Visione**: trasformare Codice Civico da "osservatorio civico" (MVP) a **giornalista investigativo automatizzato** — raccoglie ogni dato pubblico sulle cariche istituzionali italiane e li incrocia come un giornalista senza bias per far emergere pattern sospetti con catena di evidenza ricostruibile.

---

## Vincoli Operativi (decisi 2026-04-17)

1. **Zero-defect al primo deploy** di ogni sprint. Nessun "ship with known issues". Gate = blocco vero, non rubber-stamp.
2. **Sprint continuo** (niente cadenza settimanale): si passa allo sprint successivo solo dopo Gate passato.
3. **F12 deferred all'ultimo** (fonti non ancora identificate). F14 ridefinito per funzionare SENZA dati monetari.
4. **Linguaggio calibrato**: mai "sospetto di reato", sempre "pattern anomalo / da verificare". Differenza legale sostanziale.
5. **Giornalisti = nodi collaterali, mai soggetti primari** di dossier (defamation/GDPR).

---

## Meccanismi Anti-Allucinazione Estesi per F10+

Oltre a M1-M4 esistenti:

- **M5 — Source-attested ingestion**: ogni riga nelle tabelle `Relationship`, `FinancialContribution`, `EntityMatch` DEVE avere `source_url NOT NULL` come constraint schema-level. Nessuna riga senza fonte può entrare nel DB.
- **M6 — Anchor-or-drop generation**: LLM output (F13, F15) passa per filtro post-processing che scarta sentence senza `[chunk_id:xxx]` o `[relationship_id:xxx]` ancorati. Output può uscire più corto ma mai non ancorato.
- **M7 — URL cache verification**: prima di usare un endpoint in codice, `curl` automatico → 200 + schema match. Build fail altrimenti.
- **M8 — Language policy linter**: regex + check LLM in CI che flagga "sospetto di reato", "coinvolto in", "responsabile di" nell'output pubblico. Sostituisce automaticamente con "pattern da verificare".

---

## Sequenza Sprint (con F12 deferred)

```
Sprint 1 — F11  Entity Resolution Ground Truth     (precondizione qualità grafo)
Sprint 2 — F10  Graph Layer + Relationship table   (fondamenta cross-entity)
Sprint 3 — F13  RAG translator con chunk citations (indipendente, sblocca F15)
Sprint 4 — F14  Cross-entity pattern detectors     (sottoset senza F12)
Sprint 5 — F12  Follow-the-money donazioni         (quando fonti identificate)
Sprint 6 — F15  Dossier LLM evidence-grounded      (sintesi narrativa)
```

Dipendenze: Sprint N+1 parte solo quando Gate Sprint N è APPROVATO da utente.

---

## Formato Gate Standard

Ogni Gate ha lo stesso formato, non negoziabile:

```
GATE Sprint <N> — <titolo>
  INPUT precondizione:  <cosa deve esistere prima>
  OUTPUT atteso:        <cosa deve esistere dopo>
  PASS CRITERIA:        <misurazione oggettiva, non "mi sembra ok">
  FAIL CRITERIA:        <condizioni specifiche che bloccano>
  REVIEW UTENTE:        <cosa deve guardare, quanto tempo>
  ROLLBACK PLAN:        <come si torna indietro se fallisce>
```

---

## Sprint 1 — F11: Entity Resolution Ground Truth

**Obiettivo**: calibrare `entity/resolver.py` con dataset labeled ≥500 pairs, misurare P/R reali. Precondizione per valore del grafo.

**Input**: resolver esistente (4 strategie: tax_code_hash, name+birth, normalized, fuzzy pg_trgm), nessuna metrica.

**Output**:
- `tools/entity_annotator.py` CLI: mostra coppie candidate (similarity 0.5-0.9), utente marca MATCH / NON_MATCH / UNSURE
- Dataset `tests/fixtures/entity_resolution_ground_truth.csv` con ≥500 pairs labellati
- Test `tests/test_entity_resolver_calibration.py` (L5): fallisce se P<0.95 o R<0.90
- Calibrazione soglie fuzzy con 80/20 train/test split, report in `STATUS.md`

**Task split**:
| Chi | Cosa |
|---|---|
| Claude | CLI annotator, loading da DB attuale, ranking coppie per similarity, framework metriche P/R, calibrazione soglie |
| Utente | Labeling ~500 pairs (stimato 2h con CLI ottimizzato). Non delegabile: decisione identità richiede dominio |

**Gate**:
```
PASS: P >= 0.95 AND R >= 0.90 su test set (100 pairs held out)
FAIL: qualsiasi metrica sotto soglia O annotator ha < 500 pairs labellati
REVIEW: utente guarda report P/R + 10 falsi positivi + 10 falsi negativi (15 min)
ROLLBACK: tuning soglie + re-test; se dopo 2 iterazioni non converge, rivediamo strategie
```

---

## Sprint 2 — F10: Graph Layer

**Obiettivo**: tabella `Relationship` in PostgreSQL con CTE ricorsive per traversal 2-3 hop. NO Neo4j.

**Input**: resolver calibrato (P≥0.95), DB esistente con 15 tabelle.

**Output**:
- Migration Alembic: tabella `relationships` con schema sotto
- Popolamento automatico da dati esistenti: politician→party, politician→committee, contract→buyer, contract→supplier, law→sponsor
- Endpoint `GET /api/v1/graph/{entity_type}/{id}/expand?hops=2`
- 5-10 test (unit + integration su 2-hop query)
- Constraint M5 attivo: `source_url NOT NULL`, `extraction_method NOT NULL`, `confidence NOT NULL`

**Schema**:
```sql
CREATE TABLE relationships (
  id UUID PRIMARY KEY,
  source_id UUID NOT NULL,
  source_type VARCHAR(32) NOT NULL,  -- Politician|Contract|Company|...
  target_id UUID NOT NULL,
  target_type VARCHAR(32) NOT NULL,
  kind VARCHAR(32) NOT NULL,  -- member_of|awards_to|sponsored_by|funding|...
  source_url TEXT NOT NULL,           -- M5 enforcement
  extraction_method VARCHAR(32) NOT NULL,  -- deterministic_join|user_annotated|ml_match
  confidence NUMERIC(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  as_of_date DATE,
  ingested_at TIMESTAMPTZ DEFAULT now(),
  source_checksum CHAR(64),  -- SHA256 documento originale (chain of custody)
  raw_payload BYTEA
);
CREATE INDEX idx_rel_source ON relationships(source_id, source_type);
CREATE INDEX idx_rel_target ON relationships(target_id, target_type);
```

**Task split**:
| Chi | Cosa |
|---|---|
| Claude | Migration, schema, population queries, API endpoint, CTE recursive traversal, test |
| Utente | Review schema PRIMA di migrate; review primi 20 archi popolati + spot-check su source_url randomica |

**Gate**:
```
PASS: traversal 2-hop da un politico noto torna azienda verificabile via source_url cliccabile
      + tutti i 20 primi archi hanno source_url che risolve HTTP 200
      + constraint M5 rigetta riga senza source_url (test specifico)
FAIL: qualsiasi fabbricazione di relazione non tracciabile
REVIEW: utente guarda 20 random archi, verifica 5 source_url cliccando (15 min)
ROLLBACK: DROP TABLE + ripensare schema
```

---

## Sprint 3 — F13: RAG Translator con Chunk-Level Citations

**Obiettivo**: trasformare `translator.py` da generatore black-box in generatore con ogni claim ancorato a `[Art. N, comma M]`.

**Input**: tabella `legislative_acts` esistente con testo leggi, pgvector installato.

**Output**:
- Migration Alembic: tabella `legislative_chunks(law_id, article_num, comma_num, text, embedding VECTOR(384))`
- `nlp/chunker.py`: segmenta testo legge per articolo/comma (parser law-aware, non fixed-size)
- `nlp/rag_translator.py`: nuovo modulo; retrieve top-K chunk + prompt LLM con enforcement citazione
- Endpoint `POST /api/v1/laws/{id}/translate?with_citations=true`
- Parser output M6: ogni sentence senza `[Art. N, comma M]` viene scartata o marcata "non verificabile"
- Frontend: click su citazione evidenzia chunk originale

**Task split**:
| Chi | Cosa |
|---|---|
| Claude | Migration, chunker, RAG pipeline, prompt engineering, M6 filter, endpoint, frontend highlight |
| Utente | Scegliere 5 leggi di cui conosce il contenuto; review output per controllo anchor corretto |

**Gate**:
```
PASS: su 5 leggi scelte da utente, ogni claim generato risolve a chunk esistente
      + zero claim non ancorati nell'output visibile
      + highlight frontend funziona click-through
FAIL: qualsiasi sentence non ancorata lasciata passare; citazione che risolve a chunk errato
REVIEW: utente legge 5 traduzioni complete, verifica 10 citazioni random (30 min)
ROLLBACK: tuning prompt + soglia retrieval; se 2 fallimenti consecutivi → rivedere modello LLM
```

---

## Sprint 4 — F14: Cross-Entity Pattern Detectors (subset senza F12)

**Obiettivo**: 3-5 pattern detector che attraversano il grafo F10. Esclusi pattern che richiedono `FinancialContribution` (deferred a dopo F12).

**Input**: grafo F10 popolato + resolver F11 calibrato.

**Output**: `anomaly/cross_entity.py` con 3-5 pattern funzionanti. Ogni pattern emette `AnomalyFlag` con `evidence_chain` (JSON con lista (node_id, relationship_id, source_url) ricostruibile). Endpoint `GET /api/v1/investigations/{pattern_id}/matches`. Frontend: pagina `/indagini`.

**Pattern candidati (da scegliere 3-5 CON UTENTE)**:
1. **Rotazione sospetta buyer-supplier**: stesso fornitore > 50% contratti di buyer (già in REVOLVING_DOOR, ma riscritto su grafo con evidence chain)
2. **Sovrapposizione di carica**: politico X in commissione Y vota su norma che riguarda settore dove ha lavorato (fonte: CV politico)
3. **Cluster territoriale anomalo**: ente pubblico regione X assegna ripetutamente a fornitore con sede regione Y molto distante
4. **Self-contracting**: buyer e supplier condividono almeno un amministratore (richiede F12 per beneficiari effettivi → **deferred**)
5. **Vote-against-constituency**: politico vota norma contraria al profilo elettorale della sua circoscrizione

**Task split**:
| Chi | Cosa |
|---|---|
| Claude | Implementazione SQL/Python di pattern approvati, test, endpoint, frontend |
| Utente | **Selezionare quali 3-5 pattern sono davvero rivelatori nella realtà italiana**. Validare top 10 match per ciascun pattern (30 min) |

**Gate**:
```
PASS: 3+ pattern implementati; top 10 match di CIASCUNO review-ati da utente senza falsi positivi
      + ogni flag ha evidence_chain cliccabile che risolve ai source_url originali
      + M6 attivo: nessun AnomalyFlag senza evidence_chain
FAIL: >10% falsi positivi in top 10 di qualsiasi pattern (zero-defect constraint)
REVIEW: utente review 10 top match per pattern = 30-50 min totali
ROLLBACK: declass pattern a LOW/disabled, re-tune condizioni
```

---

## Sprint 5 — F12: Follow-the-Money Electoral Donations

**Obiettivo**: ingerire donazioni partitiche/elettorali. Chiude il circuito "chi paga → chi decide → chi vince appalto".

**Precondizione bloccante**: **Utente identifica fonti verificate (con esempio curl/URL funzionante)**. Senza questo, sprint non parte.

**Fonti da identificare (tua ricerca)**:
- Commissione Garanzia Elettorale (Camera) — rendiconti annuali partiti
- Corte dei Conti — bilanci partiti depositati
- OpenPolis — eventuali aggregati
- Dichiarazioni reddituali parlamentari (allegati Camera/Senato)

**Output**:
- Tabella `financial_contributions(donor_id, donor_type, recipient_id, recipient_type, amount, currency, date, source_url, source_type)` con constraint M5
- Ingestor per ≥2 fonti
- Auto-popolamento di `relationships` kind=`funding`
- Nuovi pattern F14 ora sbloccati (es. "supplier finanzia partito del ministro firmatario del decreto che ha bandito gara vinta dal supplier")

**Task split**:
| Chi | Cosa |
|---|---|
| Utente | **Ricerca fonti esatte, URL funzionanti, formato risposta. 30 min di tua ricerca = settimane risparmiate di mie allucinazioni** |
| Claude | Ingestor una volta che fonti sono chiare, test, popolazione relationships |

**Gate**:
```
PASS: >= 2 ingestor funzionanti, dati importati verificabili via source_url
      + 10 random record cross-checked con fonte originale dall'utente
      + constraint M5 attivo
FAIL: discrepanza >5% tra dati ingeriti e fonte originale
REVIEW: utente spot-check 10 record = 20 min
ROLLBACK: disabilita ingestor fonte divergente, re-parse
```

---

## Sprint 6 — F15: Dossier LLM Evidence-Grounded

**Obiettivo**: layer narrativo. Dossier auto-compilato per ogni figura istituzionale, **ogni frase ancorata**.

**Input**: grafo F10 popolato + pattern F14 attivi + (opzionale) donazioni F12.

**Output**:
- `nlp/dossier_generator.py`: LLM con prompt strutturato anchor-or-drop
- Endpoint `GET /api/v1/dossier/{entity_type}/{id}` esteso con `narrative` field
- M6+M8 attivi: parser output verifica citazioni AND language policy linter
- Dashboard: sezione "Narrativa" visibile ma con warning "Generato da AI — verifica tu le fonti"

**Task split**:
| Chi | Cosa |
|---|---|
| Claude | Generator, prompt engineering, M6 enforcement, M8 linter, frontend integration |
| Utente | **Review dei primi 20 dossier prima di esporre al pubblico. Defamation audit. Language audit** |

**Gate**:
```
PASS: 20 dossier generati, review utente: ZERO affermazioni non ancorate; ZERO linguaggio accusatorio
      + M8 linter non flagga nulla in output
      + test: dossier inventato di proposito (politico fittizio) produce narrative vuota (M6 enforcement)
FAIL: 1+ affermazione non ancorata negli ultimi 20 dossier; 1+ uso di "sospetto di reato"/"coinvolto"
REVIEW: utente legge 20 dossier completi = 2h (SPRINT PESANTE, zero-defect)
ROLLBACK: disabilita endpoint pubblico; tuning prompt; re-loop
```

---

## Fasi ESPLICITAMENTE DEFERRED

- **Neo4j / DB grafo dedicato**: sine die. PostgreSQL+CTE copre 2-3 hop. Neo4j valore >5 hop (raro in giornalismo).
- **Whistleblowing Tor/PGP**: progetto separato (SecureDrop).
- **Time Series tribunali**: valore giornalistico basso.
- **Streaming ANAC parser multi-anno**: swap 4GB basta per ora; riprendere per storico 2020-oggi.

---

## Gap Trasversali da Integrare in F10+

### Adversarial Resistance
- Input sanitization su SPARQL upstream (Camera/Senato)
- Rate limiting per user autenticato (non solo IP)
- Detection variazioni sospette nomi (potenziale evasione resolver)

### Chain of Custody (parte di M5 enforcement)
Ogni dato ingerito ha: `source_url`, `ingested_at`, `source_checksum` (SHA256), opzionale `raw_payload` per dispute/audit. Enforced in schema Sprint 2 (F10).

---

## Budget Errori (Zero-Defect Policy)

| Tipo errore | Tolleranza |
|---|---|
| False positive pattern detector pubblicato | **0** |
| Dossier con claim non ancorato | **0** |
| Relationship senza source_url | **0** (schema constraint) |
| Language policy violation in output pubblico | **0** (M8 blocking) |
| URL fabbricato da Claude | **0** (M7 verify) |
| Falso positivo in dataset ground truth | ≤5% (comunicato esplicitamente nel report) |

Qualsiasi violazione di soglia 0 = ROLLBACK immediato dello sprint.

---

## Riferimenti

- `project_codice_civico.md` — visione alto livello
- `project_codice_civico_deploy.md` — stato deploy live
- `feedback_expert_proof_standard.md` — standard anti-superficialità
- `STATUS.md` — stato corrente cross-session
- `KNOWN_ISSUES.md` — registro bug con causa radice
