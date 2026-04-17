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

- **M5 — Source-attested ingestion + temporalità**: ogni riga nelle tabelle a evidenza (`persons`, `mandates`, `party_memberships`, `relationships`, `financial_contributions`, `entity_matches`) DEVE avere `source_url NOT NULL` come constraint schema-level. Per tabelle ad arco temporale (`mandates`, `party_memberships`, `relationships`): `start_date`/`valid_from NOT NULL` obbligatorio — nessuna relazione senza finestra di validità. Nessuna riga senza fonte né senza temporalità può entrare nel DB.
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

> **UPDATE 2026-04-17**: Sprint chiuso come NON APPLICABILE sui dati attuali — vedi `KNOWN_ISSUES.md` EC-015. Motivo: pipeline Camera/Senato ingerisce solo legislatura 19; caso "cross-legislatura" strutturalmente assente; codice fiscale non esposto da SPARQL; api3.openpolis.it giù. Trigger di rivisitazione: (a) ingestione legislature storiche, (b) duplicati emersi come cluster simmetrici in F10, (c) precondizione F15 dossier. F10 può partire senza resolver calibrato perché URI Camera `drNNNN` è deterministicamente persona-stabile.

**Obiettivo originale** (riprendere al primo trigger): calibrare `entity/resolver.py` con dataset labeled ≥500 pairs, misurare P/R reali. Precondizione per valore del grafo su fonti eterogenee.

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

## Sprint 2 — F10: Graph Layer (modello bitemporale)

**Obiettivo**: schema bitemporale in PostgreSQL — entità stabili (`persons`) + archi temporali (`mandates`, `party_memberships`, `relationships` generico) con `valid_from`/`valid_to` obbligatori, CTE ricorsive per traversal 2-3 hop. NO Neo4j.

**Input**: DB esistente con 15 tabelle (politicians è record-per-legislatura, superato). Resolver F11 deferred (EC-015): non blocca F10 perché i politici Camera hanno identificatore deterministico nativo (`drNNNN`).

### Scoperta architetturale (2026-04-17)

L'ontologia `dati.camera.it` supporta nativamente il modello a entità temporale:

1. Classe `ocd:mandatoCamera` con predicati `startDate`, `endDate`, `rif_deputato`, `rif_leg`, `motivoTermine`, `convalida`, `tipoProclamazione`.
2. URI deputato segue pattern `deputato.rdf/drNNNN_LL` dove `drNNNN` è persona-stabile tra legislature (verificato live: `dr3325` presente in leg. 16, 17, 18, 19, 20, 21, 22 del Regno) — MA valido solo per leg ≥ 16 (prefisso `dr`); legislature storiche usano prefissi `d`/`dd` con ID non stabile.

### Scoperta architetturale Senato (2026-04-17, task F10 #1)

Verificato live contro `https://dati.senato.it/sparql`:

1. **URI senatore è persona-stabile**: pattern `senatore/{N}` (solo intero, niente suffisso). Verifica: `senatore/3923` (Azzollini) compare in 5 legislature (13-17). `osr:Senatore` = 6.269 istanze aggregato multi-legislatura.
2. **Predicato persona→mandato**: `osr:mandato`. Classe mandato: `ocd:mandatoSenato` (namespace Camera riusato). URI mandato: `mandato/S_{leg}_{id}_{k}`.
3. **Predicati mandato Senato**: `osr:inizio` (6633), `osr:fine` (6428), `osr:legislatura` (int), `osr:tipoMandato`, `osr:tipoFineMandato`, `osr:regioneElezione`, `osr:tipoElezione`, `osr:collegioElezione`, `osr:dataNomina`, `osr:dataComunicazione`, `osr:dataConvalida`.
4. **Link Camera↔Senato via `owl:sameAs` indiretto** (2.379 triple verificate): per senatori che hanno avuto anche mandato Camera, l'endpoint Senato pubblica `mandato/C_{leg}_{id}` con `owl:sameAs` a `dati.camera.it/ocd/deputato.rdf/{prefix}{id}_{leg}`. Catena: `senatore/N --osr:mandato--> mandato/C_{leg}_* --owl:sameAs--> camera.it/deputato.rdf/{prefix}{id}_{leg}`. **Nessun bisogno di Wikidata/OpenPolis per MVP**.
5. **Party vs commissione**: `osr:Afferenza` (26.229) è appartenenza a COMMISSIONI/ORGANI (`commissione`, `organo`, `carica`) → non mappa su `party_memberships`. Per party membership usare `ocd:aderisce` (namespace Camera, riusato anche sul senatore).

**Conseguenza**: ridisegnare granularità di ingestione. Si passa da `?d a ocd:deputato` (record istantaneo per legislatura) a `?m a ocd:mandatoCamera` (arco temporale Persona→Camera). Niente deduplicazione statistica per Camera leg 19 (MVP). Link Camera-Senato tramite catena `owl:sameAs` sopra (deterministico).

**Residuo aperto (non bloccante MVP)**:
- Legislature Camera storiche (<16): prefissi `d`/`dd`, ID non stabile → affrontato quando riaperto EC-015 (F11) per ingestione leg storiche.
- `osr:Afferenza` (commissioni) fuori scope core F10; riattivabile in Sprint 4 F14 per pattern "sovrapposizione di carica".

### Output

- Migration Alembic: 5 tabelle nuove (`persons`, `person_external_ids`, `mandates`, `party_memberships`, `relationships`) come da schema sotto. Tabella `politicians` esistente mantenuta per ora in modalità view/compat; deprecazione tracciata come task separato.
- CameraIngestor rivolto a `ocd:mandatoCamera`: estrae mandati per legislatura 19 (come oggi) ma con `startDate`/`endDate` popolati. Person_id Camera estratto da regex `dr(\d+)` su URI deputato (leg ≥ 16). Namespace `camera_leg` per external_id per-legislatura.
- SenatoIngestor rivolto a `ocd:mandatoSenato`: estrae mandati via predicato `osr:mandato` del senatore, con `osr:inizio`/`osr:fine`/`osr:legislatura`. Person_id Senato estratto da regex `senatore/(\d+)` — persona-stabile nativo. Link Camera↔Senato popolato via query `osr:mandato → C_* → owl:sameAs → camera deputato URI` (catena verificata live).
- Popolamento automatico `relationships` da dati esistenti: contract→buyer, contract→supplier, law→sponsor, speech→speaker, vote→voter (quando presenti).
- Endpoint `GET /api/v1/graph/{entity_type}/{id}/expand?hops=2&as_of=YYYY-MM-DD` — query bitemporale: quali archi erano attivi alla data X?
- 5-10 test (unit sul parser URI, integration su query 2-hop, regression M5 schema rejection).
- Constraint M5 esteso attivo: `source_url NOT NULL`, `extraction_method NOT NULL`, `confidence NOT NULL`, `valid_from NOT NULL`.

### Schema

```sql
-- Persona: entità stabile (prevista successiva migrazione politicians→persons)
CREATE TABLE persons (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  primary_full_name TEXT NOT NULL,
  birth_date DATE,
  ingested_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_persons_full_name ON persons USING GIN (primary_full_name gin_trgm_ops);

-- Identificatori esterni per persona (M5: source_url per ogni ID)
CREATE TABLE person_external_ids (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  namespace VARCHAR(32) NOT NULL,          -- 'senato'|'camera_leg'|'wikidata'|'openpolis'
  external_id TEXT NOT NULL,               -- '63' | 'dd35040_14' | 'Q1234'
  source_url TEXT NOT NULL,                -- M5
  source_checksum CHAR(64),
  ingested_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (namespace, external_id)
);
CREATE INDEX idx_pei_person ON person_external_ids(person_id);
CREATE INDEX idx_pei_lookup ON person_external_ids(namespace, external_id);

-- Mandati parlamentari: archi temporali Persona → Camera/Senato
CREATE TABLE mandates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  chamber VARCHAR(10) NOT NULL CHECK (chamber IN ('camera','senato')),
  legislature INT NOT NULL,
  start_date DATE NOT NULL,               -- M5: valid_from NOT NULL
  end_date DATE,                          -- NULL = in corso
  motivo_termine TEXT,
  source_url TEXT NOT NULL,               -- M5
  source_checksum CHAR(64),               -- SHA256 chain-of-custody
  ingested_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (person_id, chamber, legislature, start_date)
);
CREATE INDEX idx_mandates_person ON mandates(person_id);
CREATE INDEX idx_mandates_temporal ON mandates(start_date, end_date);

-- Appartenenze partitiche: altri archi temporali
CREATE TABLE party_memberships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  party TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE,
  source_url TEXT NOT NULL,               -- M5
  source_checksum CHAR(64),
  ingested_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_party_person ON party_memberships(person_id);
CREATE INDEX idx_party_temporal ON party_memberships(start_date, end_date);

-- Relationships generiche: archi cross-entità con temporalità obbligatoria
CREATE TABLE relationships (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id UUID NOT NULL,
  source_type VARCHAR(32) NOT NULL,       -- Person|Contract|Company|LegislativeAct|Tribunal|...
  target_id UUID NOT NULL,
  target_type VARCHAR(32) NOT NULL,
  kind VARCHAR(32) NOT NULL,              -- member_of|awards_to|sponsored_by|funding|speaker_of|...
  valid_from DATE NOT NULL,               -- M5: temporalità obbligatoria
  valid_to DATE,                          -- NULL = ongoing
  source_url TEXT NOT NULL,               -- M5
  extraction_method VARCHAR(32) NOT NULL, -- deterministic_join|sparql_join|user_annotated|ml_match
  confidence NUMERIC(3,2) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
  ingested_at TIMESTAMPTZ DEFAULT now(),
  source_checksum CHAR(64),
  raw_payload BYTEA
);
CREATE INDEX idx_rel_source ON relationships(source_id, source_type);
CREATE INDEX idx_rel_target ON relationships(target_id, target_type);
CREATE INDEX idx_rel_temporal ON relationships(valid_from, valid_to);
CREATE INDEX idx_rel_kind ON relationships(kind);
```

### Query bitemporali tipiche

```sql
-- Mandati attivi a una data
SELECT p.full_name, m.chamber, m.legislature
FROM persons p JOIN mandates m ON m.person_id = p.id
WHERE m.start_date <= :as_of
  AND (m.end_date IS NULL OR m.end_date >= :as_of);

-- Traversal 2-hop da persona con filtro temporale
WITH RECURSIVE expand(id, type, hop, path) AS (
  SELECT :start_id::uuid, :start_type::text, 0, ARRAY[:start_id::uuid]
  UNION ALL
  SELECT r.target_id, r.target_type, e.hop + 1, e.path || r.target_id
  FROM expand e JOIN relationships r
    ON r.source_id = e.id AND r.source_type = e.type
  WHERE e.hop < 2
    AND r.valid_from <= :as_of
    AND (r.valid_to IS NULL OR r.valid_to >= :as_of)
    AND NOT r.target_id = ANY(e.path)
) SELECT * FROM expand;
```

### Pattern SPARQL ingestione

```sparql
# Camera: mandati (arco temporale), NON deputati (istantaneo)
SELECT ?mandato ?dep ?startDate ?endDate ?leg ?motivo WHERE {
  ?mandato a ocd:mandatoCamera ;
           ocd:rif_deputato ?dep ;
           ocd:startDate ?startDate ;
           ocd:rif_leg ?leg .
  OPTIONAL { ?mandato ocd:endDate ?endDate }
  OPTIONAL { ?mandato ocd:motivoTermine ?motivo }
  FILTER(?leg = <http://dati.camera.it/ocd/repubblica_19>)
}
```

Person ID: regex `dr(\d+)_\d+` su URI `?dep` → gruppo 1 → `external_id = "camera:dr{N}"`.

### Task split

| Chi | Cosa |
|---|---|
| Claude | ✅ DONE — Verifica empirica `osr:mandato` Senato (SPARQL live 2026-04-17). Migration, schema 5 tabelle, ingestor rewrites, population queries, endpoint, CTE traversal bitemporale, test. |
| Utente | ✅ DONE — Decisione opzione B (`person_external_ids` separata). Restano: review schema pre-migrate (30 min); review primi 20 archi + spot-check source_url (15 min). |

### Gate

```
PASS:
  - query "appartenenza partitica di persona X al 2023-05-15" risponde deterministicamente da party_memberships
  - traversal 2-hop da un parlamentare noto con as_of=2024-06-01 ritorna azienda verificabile via source_url cliccabile
  - constraint M5 rigetta INSERT senza source_url (test specifico)
  - constraint M5 esteso rigetta INSERT senza valid_from (test specifico)
  - primi 20 archi random hanno source_url che risolve HTTP 200
  - persona con mandati in ≥2 legislature ha ESATTAMENTE 1 row in persons (verifica dr3325 Camera o senatore/3923 Senato)
  - senatore che è stato anche deputato ha ≥2 rows in person_external_ids (es. senatore/63 Amoruso: `senato:63` + `camera_leg:d35040_12` + `camera_leg:dd00018_13` + ...)

FAIL:
  - qualsiasi riga senza source_url o valid_from passa l'insert
  - duplicazione persona tra legislature (bug regex person_id)
  - traversal bitemporale ritorna archi fuori finestra as_of
  - residuo Senato non documentato (nessuna nota "link Camera↔Senato differito perché X")

REVIEW utente: schema pre-migrate (30 min) + 20 archi + 5 source_url cliccati (15 min)

ROLLBACK: alembic downgrade -1; DROP TABLE persons/mandates/party_memberships/relationships; revert ingestor rewrite.
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
| Arco temporale (mandate/membership/relationship) senza valid_from | **0** (schema constraint) |
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
