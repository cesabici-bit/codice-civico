"""Tests for the clean_text helper used by SPARQL ingestors."""

from codicecivico.ingest.base import clean_text


def test_decodes_html_entities() -> None:
    """# SOURCE: actual Camera SPARQL output captured 2026-04-17 from
    dati.camera.it SELECT ?titolo WHERE { ?atto dc:title ?titolo }.
    """
    raw = (
        "RAVETTO ed altri: &quot;Modifica alla tabella A allegata al decreto "
        "del Presidente della Repubblica 26 ottobre 1972, n. 633, per la "
        "riduzione dell&rsquo;aliquota dell&rsquo;imposta sul valore aggiunto "
        "relativa ai prodotti di prima necessit&agrave; per l&rsquo;infanzia"
        "&quot; (149)"
    )
    out = clean_text(raw)
    assert out is not None
    assert "&quot;" not in out
    assert "&rsquo;" not in out
    assert "&agrave;" not in out
    assert "\u2019" in out  # right single quotation mark from &rsquo;
    assert "prima necessità" in out


def test_strips_inline_html_tags() -> None:
    """# SOURCE: SERRACCHIANI ddl title in production DB contained <em>caregiver</em>."""
    raw = 'Disposizioni per i &lt;em&gt;caregiver&lt;/em&gt; familiari'
    out = clean_text(raw)
    assert out == "Disposizioni per i caregiver familiari"


def test_none_passthrough() -> None:
    assert clean_text(None) is None


def test_empty_string_returns_none() -> None:
    assert clean_text("") is None
    assert clean_text("   ") is None


def test_already_clean_is_idempotent() -> None:
    s = "Legge ordinaria sulla riforma fiscale"
    assert clean_text(s) == s


def test_collapses_internal_whitespace() -> None:
    assert clean_text("foo    bar\n\tbaz") == "foo bar baz"


def test_preserves_accented_unicode() -> None:
    assert clean_text("Città metropolitana di Milano") == "Città metropolitana di Milano"
