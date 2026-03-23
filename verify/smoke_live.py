#!/usr/bin/env python3
"""Live smoke test — verifica senza DB che i moduli funzionino su dati reali.

Esegue:
  1. SPARQL Camera → deputati legislatura 19
  2. SPARQL Senato → senatori legislatura 19
  3. Entity resolution → normalizzazione nomi + match cross-chamber
  4. ANAC download → scarica un CIG CSV reale e lo parsa

Uso:
  python verify/smoke_live.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path so we can import codicecivico
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

# Force UTF-8 output on Windows
import io as _io
import os as _os
if _os.name == "nt":
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = _io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = PASS if condition else FAIL
    print(f"  {status}  {label}")
    if detail:
        print(f"         {detail}")
    return condition


# ---------------------------------------------------------------
# 1. SPARQL Camera dei Deputati
# ---------------------------------------------------------------

def test_camera_sparql() -> bool:
    header("1. SPARQL — Camera dei Deputati (dati.camera.it)")
    from codicecivico.ingest.base import BaseIngestor
    from codicecivico.ingest.camera import QUERY_DEPUTATI

    ok = True
    try:
        t0 = time.time()
        rows = BaseIngestor._sparql_query(
            "https://dati.camera.it/sparql", QUERY_DEPUTATI, timeout=60,
        )
        elapsed = time.time() - t0
        print(f"  Risposta in {elapsed:.1f}s — {len(rows)} deputati trovati")

        ok &= check("Almeno 100 deputati", len(rows) > 100, f"Trovati: {len(rows)}")

        # Cerco Meloni
        cognomi = {r.get("cognome", "").upper() for r in rows}
        ok &= check(
            "Meloni presente (Presidente del Consiglio, deputata leg 19)",
            "MELONI" in cognomi,
            # SOURCE: camera.it — Meloni eletta Camera circoscrizione Lazio 1
        )
        ok &= check(
            "Schlein presente (Segretaria PD, deputata leg 19)",
            "SCHLEIN" in cognomi,
            # SOURCE: camera.it — Schlein eletta Camera circoscrizione Emilia-Romagna
        )

        # Mostra primi 5
        print("\n  Esempio primi 5 deputati:")
        for r in rows[:5]:
            nome = r.get("nome", "?")
            cognome = r.get("cognome", "?")
            nascita = r.get("dataNascita", "?")
            print(f"    - {cognome} {nome} (nato: {nascita})")

    except Exception as exc:
        print(f"  {FAIL}  Errore SPARQL Camera: {exc}")
        ok = False

    return ok


# ---------------------------------------------------------------
# 2. SPARQL Senato della Repubblica
# ---------------------------------------------------------------

def test_senato_sparql() -> bool:
    header("2. SPARQL — Senato della Repubblica (dati.senato.it)")
    from codicecivico.ingest.base import BaseIngestor
    from codicecivico.ingest.senato import QUERY_SENATORI

    ok = True
    try:
        t0 = time.time()
        rows = BaseIngestor._sparql_query(
            "https://dati.senato.it/sparql", QUERY_SENATORI, timeout=60,
        )
        elapsed = time.time() - t0
        print(f"  Risposta in {elapsed:.1f}s — {len(rows)} senatori trovati")

        ok &= check("Almeno 50 senatori", len(rows) > 50, f"Trovati: {len(rows)}")

        # Cerco La Russa (Presidente del Senato)
        cognomi = {r.get("cognome", "").upper() for r in rows}
        ok &= check(
            "La Russa presente (Presidente del Senato, leg 19)",
            "LA RUSSA" in cognomi or any("LA RUSSA" in c for c in cognomi),
            # SOURCE: senato.it — Ignazio La Russa eletto Presidente Senato 13/10/2022
        )

        # Mostra primi 5
        print("\n  Esempio primi 5 senatori:")
        for r in rows[:5]:
            nome = r.get("nome", "?")
            cognome = r.get("cognome", "?")
            nascita = r.get("dataNascita", "?")
            print(f"    - {cognome} {nome} (nato: {nascita})")

    except Exception as exc:
        print(f"  {FAIL}  Errore SPARQL Senato: {exc}")
        ok = False

    return ok


# ---------------------------------------------------------------
# 3. Entity Resolution — normalize + match
# ---------------------------------------------------------------

def test_entity_resolution() -> bool:
    header("3. Entity Resolution — normalizzazione nomi")
    from codicecivico.entity.resolver import normalize_name

    ok = True
    # Casi reali di politici che hanno servito in entrambe le camere
    cases = [
        # (Camera name format, Senato name format, should_match)
        ("MELONI GIORGIA", "Meloni Giorgia", True),
        ("RENZI MATTEO", "Renzi Matteo", True),
        ("LA RUSSA IGNAZIO BENITO MARIA", "La Russa Ignazio Benito Maria", True),
        ("MELONI GIORGIA", "SCHLEIN ELLY", False),  # diversi, non devono matchare
        ("D'ALEMA MASSIMO", "D'Alema Massimo", True),
        ("DE PETRIS LOREDANA", "De Petris Loredana", True),
    ]

    print("  Test normalizzazione:")
    for name_a, name_b, should_match in cases:
        norm_a = normalize_name(name_a)
        norm_b = normalize_name(name_b)
        matched = norm_a == norm_b
        correct = matched == should_match
        status = PASS if correct else FAIL
        op = "==" if should_match else "!="
        print(f"    {status}  '{name_a}' {op} '{name_b}'")
        print(f"           norm: '{norm_a}' vs '{norm_b}'")
        ok &= correct

    return ok


# ---------------------------------------------------------------
# 4. ANAC — download e parsing CSV reale
# ---------------------------------------------------------------

def test_anac_download() -> bool:
    header("4. ANAC — Download e parsing CIG CSV reale")
    from codicecivico.ingest.anac import (
        _cig_url,
        _detect_delimiter,
        _download_zip,
        _extract_csv_from_zip,
        _parse_decimal,
        parse_cig_csv,
    )

    ok = True

    # Prova a scaricare un mese recente (2024-01 come test)
    year, month = 2024, 1
    url = _cig_url(year, month)
    print(f"  URL: {url}")

    try:
        t0 = time.time()
        zip_bytes = asyncio.run(_download_zip(url))
        elapsed = time.time() - t0

        if zip_bytes is None:
            print(f"  {WARN}  Download fallito (potrebbe essere un problema di rete/WAF)")
            print(f"         Provo con 2023-12...")
            # Fallback a un mese diverso
            year, month = 2023, 12
            url = _cig_url(year, month)
            zip_bytes = asyncio.run(_download_zip(url))
            if zip_bytes is None:
                print(f"  {FAIL}  Anche il fallback è fallito. Verifica la connessione.")
                return False

        size_mb = len(zip_bytes) / (1024 * 1024)
        print(f"  Download completato in {elapsed:.1f}s — {size_mb:.1f} MB")
        ok &= check("ZIP scaricato", True)

        # Estrai CSV
        csv_text = _extract_csv_from_zip(zip_bytes)
        ok &= check("CSV estratto dal ZIP", len(csv_text) > 0, f"{len(csv_text)} caratteri")

        # Detect delimiter
        delimiter = _detect_delimiter(csv_text)
        ok &= check(f"Delimitatore rilevato: '{delimiter}'", delimiter in (",", ";"))

        # Parse
        rows = parse_cig_csv(csv_text)
        ok &= check(f"Righe parsate: {len(rows)}", len(rows) > 0)

        if rows:
            first = rows[0]
            # Verifica campi attesi
            expected_fields = [
                "cig", "denominazione_amministrazione_appaltante",
                "cf_amministrazione_appaltante", "importo_complessivo_gara",
            ]
            present = [f for f in expected_fields if f in first]
            missing = [f for f in expected_fields if f not in first]

            ok &= check(
                f"Campi CIG presenti: {len(present)}/{len(expected_fields)}",
                len(missing) == 0,
                f"Presenti: {present}" + (f" | Mancanti: {missing}" if missing else ""),
            )

            # Se i campi attesi non ci sono, mostra quelli disponibili
            if missing:
                print(f"\n  Campi disponibili nel CSV ({len(first)} colonne):")
                for key in sorted(first.keys()):
                    print(f"    - {key}: {first[key][:60] if first[key] else '(vuoto)'}")

            # Mostra primi 3 contratti
            print(f"\n  Esempio primi 3 contratti ({year}-{month:02d}):")
            for r in rows[:3]:
                cig = r.get("cig", "?")
                buyer = (
                    r.get("denominazione_amministrazione_appaltante", "")
                    or r.get("denominazione_sa", "?")
                )
                amount = r.get("importo_complessivo_gara", "?")
                cpv = r.get("cod_cpv", "?")
                proc = r.get("tipo_scelta_contraente", "?")
                print(f"    CIG: {cig}")
                print(f"      Buyer: {buyer[:60]}")
                print(f"      Importo: €{amount} | CPV: {cpv} | Procedura: {proc[:40]}")
                print()

            # Verifica amounts parsabili
            parsable = 0
            for r in rows[:100]:
                amt = r.get("importo_complessivo_gara", "")
                if amt and _parse_decimal(amt) is not None:
                    parsable += 1
            ok &= check(
                f"Importi parsabili (primi 100): {parsable}/100",
                parsable > 80,
            )

    except Exception as exc:
        print(f"  {FAIL}  Errore: {exc}")
        import traceback
        traceback.print_exc()
        ok = False

    return ok


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("  CODICE CIVICO — Smoke Test Live (senza DB)")
    print("  Verifica connettività e parsing su dati reali")
    print("=" * 60)

    results = {}
    results["Camera SPARQL"] = test_camera_sparql()
    results["Senato SPARQL"] = test_senato_sparql()
    results["Entity Resolution"] = test_entity_resolution()
    results["ANAC Download"] = test_anac_download()

    # Riepilogo
    header("RIEPILOGO")
    all_ok = True
    for name, passed in results.items():
        status = PASS if passed else FAIL
        print(f"  {status}  {name}")
        all_ok &= passed

    print()
    if all_ok:
        print("  TUTTI I TEST PASSATI — il lavoro è corretto!")
    else:
        print("  ALCUNI TEST FALLITI — verificare i dettagli sopra.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
