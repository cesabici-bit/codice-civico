# Roadmap — Codice Civico

> **Visione**: trasformare Codice Civico da "osservatorio civico" (MVP) a **giornalista investigativo automatizzato** — uno strumento che raccoglie ogni dato pubblico sulle cariche istituzionali italiane e li incrocia come un giornalista super-razionale e privo di bias per far emergere pattern sospetti con catena di evidenza ricostruibile.

## Regole trasversali

1. **Giornalisti = nodi collaterali, mai soggetti primari** di dossier (cittadini privati → rischio diffamazione/GDPR). Esempio OK: "articolo X firmato da Y, Y riceve finanziamento da W". Esempio NOT OK: dossier dedicato su Y.
2. **Linguaggio calibrato**: mai "sospetto di reato". Sempre "pattern anomalo", "possibile conflitto di interesse da verificare". Differenza legale sostanziale.
3. **Ogni claim prodotto dal sistema deve avere evidence chain ricostruibile**: fonte, data di ingest, hash del documento originale. No affermazioni senza ancora.
4. **Discussione + task split con utente PRIMA di ogni fase**. Non partire con implementazione senza allineamento.

## Stato MVP (F0-F9) — COMPLETATO

Deploy LIVE su `http://46.225.219.136/` (Hetzner CX22):
- 4 moduli core: Promise Tracker, Anomaly Detector, Justice Map, Legislative Translator
- 15 tabelle ORM, 19 endpoint API, 11 route frontend Next.js 15
- DB ingested: 668 politici, 250 atti, 144 tribunali, 1540 CourtStat
- 203 test verdi (L1+L2+L3)

---

## Post-MVP — Fasi Prioritizzate

Ordine di attacco deciso in sessione 2026-04-17 dopo discussione critica Gemini.

### F10 — Relationship/Graph Layer (fondamenta)

**Obiettivo**: tabella `Relationship` in PostgreSQL per modellare edge esplicite persona↔persona, persona↔azienda, persona↔denaro, persona↔evento. NO Neo4j — CTE ricorsive su Postgres bastano fino a 2-3 hop.

**Schema proposto**:
```
Relationship(
  id uuid,
  source_id uuid,
  source_type enum(Politician, Magistrate, Company, InstitutionalFigure, Contract, LegislativeAct),
  target_id uuid,
  target_type enum(...),
  kind enum(family, business_partner, employer, funding, vote_for, award_to, ...),
  evidence_source varchar,   -- URL della fonte
  evidence_url varchar,
  confidence float 0-1,
  as_of_date date,
  created_at timestamp
)
```

**Pass/fail**:
- Query di test: "trova tutte le aziende entro 2 hop da un politico X"
- Indici su (source_id, source_type) e (target_id, target_type)
- Almeno 1 pattern detector che usi la tabella (es. REVOLVING_DOOR riscritto)

**Chi fa cosa**:
- Claude: schema, migration Alembic, query helper, 5-10 test
- Utente: review schema prima di migrare

**Perché questa prima**: senza Relationship, F12-F14 non hanno dove scrivere.

---

### F11 — Entity Resolution Ground Truth & Metriche

**Obiettivo**: calibrare il resolver esistente con un dataset labeled di ≥500 coppie annotate manualmente. Misurare precision/recall.

**Motivazione (gap che Gemini non vede)**: il grafo ha valore solo se "Mario Rossi" non appare 5 volte come 5 nodi diversi. Oggi `entity/resolver.py` ha 4 strategie (tax_code_hash, name+birth, normalized, fuzzy pg_trgm) ma **non misuriamo precision/recall**. Senza questa calibrazione, ogni pattern detector costruito sopra il grafo amplifica gli errori invece di catturarli.

**Deliverables**:
- Tool CLI di annotazione: mostra coppie "sospette" (similarity 0.5-0.9), utente marca MATCH/NON_MATCH
- Dataset `tests/fixtures/entity_resolution_ground_truth.csv` con ≥500 coppie
- Test L5 in `test_entity_resolver.py` che misura P/R sul dataset e fallisce se P<0.95 o R<0.90
- Calibrazione soglie fuzzy sul training set (80/20 split)

**Chi fa cosa**:
- Claude: tool annotazione, framework test, calibrazione
- **Utente: annotazione manuale delle ~500 coppie** (operazione non delegabile, richiede dominio)

**Pass/fail**: P ≥ 0.95 e R ≥ 0.90 sul test set.

---

### F12 — Follow the Money: Electoral Donations

**Obiettivo**: ingerire i finanziamenti elettorali e privati ricevuti da partiti/candidati per chiudere il circuito investigativo (oggi abbiamo solo appalti OUT, manca il cash IN).

**Fonti da ricercare (tua parte)**:
- Commissione Garanzia Elettorale presso la Camera — rendiconti annuali partiti
- Corte dei Conti — bilanci partiti depositati
- OpenPolis — potrebbe avere aggregati
- Dichiarazioni dei redditi parlamentari (allegati Camera/Senato)
- 5x1000 (destinazioni)

**Deliverables**:
- Tabella `FinancialContribution(donor_id, donor_type, recipient_id, recipient_type, amount, date, source_url, source_type)`
- Ingestor per almeno 2 fonti principali
- Relationship rows kind=`funding` popolate automaticamente dai contributi ingeriti

**Chi fa cosa**:
- Utente: **ricerca fonti esatte** (API? scraping? download PDF?) — task non delegabile, serve orientamento politico-amministrativo italiano
- Claude: ingestor una volta identificate le fonti

**Valore**: è il killer feature giornalistica. Cross-referenziare vincitore-appalto con finanziatore-partito-del-ministro-firmatario è esattamente il pattern core.

---

### F13 — RAG con Citazioni Chunk-Level per Traduzione Leggi

**Obiettivo**: trasformare `translator.py` da riassumatore black-box a **testimone con citazioni puntuali**. Ogni claim dell'LLM porta con sé l'ID del chunk (articolo/comma) da cui deriva.

**Motivazione**: in contesto civico, l'allucinazione AI è un rischio legale e reputazionale enorme. Un giudice che legga l'output deve poter ricostruire la fonte esatta. Questo è il punto più forte dell'analisi Gemini.

**Architettura**:
- Storicizzazione leggi a granularità di **articolo/comma** in nuova tabella `LegislativeChunk(law_id, article_num, comma_num, text, embedding_vector)`
- Embedding di ogni chunk con MiniLM-L12 (già usato)
- Retrieval: per ogni domanda, prendo top-K chunk più rilevanti
- Prompt LLM include chunk IDs; output deve citare esplicitamente `[Art. 3, comma 2]`
- Parser output verifica che ogni affermazione abbia almeno una citazione → altrimenti marca come "non verificabile"

**Deliverables**:
- Nuova migration Alembic per `LegislativeChunk`
- `nlp/chunker.py`: segmenta testo legge in chunks
- `nlp/rag_translator.py`: nuovo modulo (affianca `translator.py`, non lo sostituisce subito)
- Endpoint API `POST /laws/{id}/translate?with_citations=true`
- Frontend: highlight del testo originale al click su una citazione

**Pass/fail**: su 10 leggi campione, ogni claim generato dall'LLM ha ≥1 citazione che risolve a chunk esistente nel DB.

---

### F14 — Cross-Entity Pattern Detectors

**Obiettivo**: pattern detector che attraversano il grafo costruito in F10-F12. Oggi `anomaly/` guarda solo `Contract` in isolamento.

**Pattern esempio**:
- "Parlamentare X ha votato norma Y che favorisce azienda Z il cui socio di minoranza è W che è stato socio di X in precedenza"
- "Ministro A ha firmato decreto B; azienda C ha vinto appalto D dal ministero di A; C ha finanziato partito di A"
- "Magistrato E ha giudicato caso su azienda F; F ha finanziato campagna di politico G che ha nominato E a carica Y"

**Deliverables**:
- `anomaly/cross_entity.py`: funzioni che compongono query sul grafo + verificano evidence chain
- Ogni pattern emette `AnomalyFlag` con `evidence_chain` (lista di (node_id, relationship_id) ricostruibile)
- Frontend: pagina `/indagini` con visualizzazione grafo + catena di evidenza

**Pass/fail**: 3 pattern funzionanti con output ispezionabile da utente.

**Dipendenze**: F10 + F11 + F12 devono essere complete.

---

### F15 — Dossier LLM Evidence-Grounded

**Obiettivo**: layer narrativo sopra tutto. Un LLM produce il "dossier" auto-compilato per ogni figura istituzionale, ma ogni frase è ancorata a una evidenza verificabile.

**Architettura**:
- Input: entity_id (Politician/Magistrate/InstitutionalFigure)
- Step 1: query grafo per raccogliere tutti i nodi connessi + evidenze
- Step 2: LLM con prompt strutturato: "Genera narrativa sul soggetto. OGNI affermazione deve citare la relationship_id o il source_url da cui deriva"
- Step 3: parser output verifica citazioni; rimuove frasi non ancorate
- Output: dossier narrativo + lista citazioni sempre visibili al lettore

**Pass/fail**: su 5 politici campione noti, il dossier non contiene affermazioni non ancorate. Review umana manuale.

**Dipendenze**: F10-F14 complete.

---

## Fasi ESPLICITAMENTE DEFERRED (discusse e rimandate)

Queste sono idee valide ma non affrontiamo ora per i motivi indicati:

- **Neo4j / DB grafo dedicato**: rimandato sine die. PostgreSQL con CTE ricorsive copre 80% dei casi a 2-3 hop. Neo4j guadagna valore sopra 5+ hop, scenario raro in giornalismo reale.
- **Whistleblowing Tor/PGP**: progetto SEPARATO, non scope Codice Civico. Hosting whistleblower ha esposizione legale diversa (privilegio giornalistico, protezione subpoena). Usare SecureDrop quando sarà il momento.
- **Time Series Forecasting per tribunali**: valore giornalistico basso. Prevedere collasso tribunale serve al Ministero, non all'investigatore.
- **Streaming ANAC parser**: utile per ingest multi-anno, oggi gestito con swap 4GB su CX22. Se servirà storico 2020-oggi, riprendere.

---

## Gap di sicurezza da affrontare (trasversali)

Non sono fasi ma pattern da integrare in F10+:

### Adversarial Resistance
Se il sistema diventa visibile, i profilati avranno incentivo a manipolarlo.
- Input sanitization sui campi testo libero SPARQL (Camera/Senato potrebbero diventare vettori injection)
- Hash di integrità sul dato ingerito (chain of custody dall'input, non solo sul claim AI)
- Rate limiting per utente autenticato (oggi solo per IP)
- Detection di variazioni sospette nel nome (famigliari che potrebbero cercare di scappare al resolver)

### Chain of Custody
Ogni dato nel DB deve avere:
- `source_url` (dove l'abbiamo preso)
- `ingested_at` (quando)
- `source_checksum` (hash SHA256 del documento originale al momento dell'ingest)
- `raw_payload` opzionale (bytea) per dispute/audit

Da integrare nello schema in F10.

---

## Riferimenti memoria

- `project_codice_civico.md` — visione alto livello
- `project_codice_civico_deploy.md` — stato deploy live, ANAC retry in corso
- `feedback_codice_civico_deploy_pitfalls.md` — 6 Docker gotchas imparati in F9
- `STATUS.md` — stato corrente progetto (cross-session)
- `KNOWN_ISSUES.md` — registro bug con causa radice
