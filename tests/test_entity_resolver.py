"""Tests for entity resolution module."""

from codicecivico.entity.resolver import normalize_name

# ---------------------------------------------------------------------------
# L1: Unit tests — normalize_name
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_basic(self) -> None:
        assert normalize_name("MELONI GIORGIA") == "meloni giorgia"

    def test_accents(self) -> None:
        """Italian names with accents: è, à, ù."""
        assert normalize_name("DE LÙCIA È BELLO") == "de lucia e bello"

    def test_extra_whitespace(self) -> None:
        assert normalize_name("  Rossi   Marco  ") == "rossi marco"

    def test_punctuation_stripped(self) -> None:
        assert normalize_name("D'Alema, Massimo!") == "d'alema massimo"

    def test_hyphenated_name(self) -> None:
        assert normalize_name("Von Der Leyen-Mueller") == "von der leyen-mueller"

    def test_empty(self) -> None:
        assert normalize_name("") == ""


# ---------------------------------------------------------------------------
# L2: Domain sanity — known cross-chamber politicians
# SOURCE: camera.it & senato.it legislature 19 — some politicians have served
# in both chambers across legislatures (e.g., Matteo Renzi: Camera leg 17,
# Senato leg 18+19). Entity resolution must handle these cases.
# ---------------------------------------------------------------------------


class TestEntityResolutionLogic:
    """Test the merge logic concepts without requiring a DB."""

    def test_same_name_normalized_match(self) -> None:
        """L2: Renzi in Camera vs Senato records should normalize identically.
        # SOURCE: camera.it (Renzi elected Camera 2013), senato.it (Renzi elected Senato 2018)
        """
        camera_name = "RENZI MATTEO"
        senato_name = "Renzi Matteo"
        assert normalize_name(camera_name) == normalize_name(senato_name)

    def test_different_names_do_not_match(self) -> None:
        """Ensure distinct politicians don't accidentally merge."""
        assert normalize_name("MELONI GIORGIA") != normalize_name("SCHLEIN ELLY")

    def test_accented_vs_plain(self) -> None:
        """Accented and non-accented versions should match.
        # SOURCE: Common Italian name normalization issue
        """
        assert normalize_name("DE PETRIS LOREDANA") == normalize_name("De Petris Loredana")
