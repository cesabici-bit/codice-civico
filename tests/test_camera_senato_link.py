r"""Tests for F10 ST-10.4 — Camera↔Senato link via ``owl:sameAs``.

Target: `ingest/senato.py::_link_camera_senato_sameas` (logic-only unit
tests; DB-dependent integration left to live ingest).

Oracles used (L2):
- Live SPARQL dati.senato.it on 2026-04-18 — senator/5799 has Camera
  mandates in legs 14-18: leg 14 uses historical ``dd`` prefix (must be
  skipped per EC-015), legs 15-18 use modern ``d`` prefix with the same
  stable id ``d300246`` (must dedup to a single camera external id).
"""

import json
from pathlib import Path

from codicecivico.ingest.camera import parse_camera_person_id
from codicecivico.ingest.senato import (
    extract_sameas_camera_link,
    parse_senato_person_id,
)

FIXTURES = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# L1: extract_sameas_camera_link — pure logic
# ---------------------------------------------------------------------------


class TestExtractSameasLink:
    """Pure function mapping a SPARQL row to a (senato_id, camera_id) pair."""

    def test_modern_camera_link_accepted(self) -> None:
        row = {
            "sen": "http://dati.senato.it/senatore/32898",
            "sameAs": "http://dati.camera.it/ocd/deputato.rdf/d307708_18",
        }
        link = extract_sameas_camera_link(row)
        assert link == ("32898", "d307708")

    def test_historical_dd_prefix_rejected(self) -> None:
        """EC-015/EC-016: historical ``dd`` prefix is not person-stable.

        # SOURCE: senator/5799 leg 14 sameAs dd300246_14 (live 2026-04-18)
        """
        row = {
            "sen": "http://dati.senato.it/senatore/5799",
            "sameAs": "http://dati.camera.it/ocd/deputato.rdf/dd300246_14",
        }
        assert extract_sameas_camera_link(row) is None

    def test_missing_fields_return_none(self) -> None:
        assert extract_sameas_camera_link({}) is None
        assert extract_sameas_camera_link({"sen": "x"}) is None
        assert extract_sameas_camera_link({"sameAs": "y"}) is None

    def test_malformed_uris_rejected(self) -> None:
        row = {
            "sen": "not-a-uri",
            "sameAs": "http://dati.camera.it/ocd/deputato.rdf/d302103_19",
        }
        assert extract_sameas_camera_link(row) is None

    def test_non_camera_target_rejected(self) -> None:
        """owl:sameAs pointing outside dati.camera.it must be dropped."""
        row = {
            "sen": "http://dati.senato.it/senatore/1",
            "sameAs": "http://example.org/somewhere",
        }
        assert extract_sameas_camera_link(row) is None


# ---------------------------------------------------------------------------
# L2: fixture reflects live SPARQL shape and end-to-end parsing
# ---------------------------------------------------------------------------


class TestSameasFixture:
    def test_fixture_loads_five_rows(self) -> None:
        data = json.loads((FIXTURES / "senato_sameas.json").read_text())
        assert len(data["results"]["bindings"]) == 5

    def test_senator_5799_yields_one_stable_camera_id_after_dedup(self) -> None:
        """Senator 5799 has 3 rows (leg 14 dd, leg 15 d, leg 16 d).
        After parsing + dedup we expect ONE camera stable id: d300246.
        The dd row is dropped per EC-015.
        """
        data = json.loads((FIXTURES / "senato_sameas.json").read_text())
        rows = [
            {k: v["value"] for k, v in b.items() if k != "mandato"}
            for b in data["results"]["bindings"]
        ]
        sen_5799 = [r for r in rows if r["sen"].endswith("/5799")]
        assert len(sen_5799) == 3  # raw

        links = {extract_sameas_camera_link(r) for r in sen_5799}
        links.discard(None)
        # After regex filter + set dedup, only the modern stable id remains
        assert links == {("5799", "d300246")}

    def test_all_modern_rows_extract_cleanly(self) -> None:
        """Each row with a modern ``d`` prefix produces a usable link."""
        data = json.loads((FIXTURES / "senato_sameas.json").read_text())
        modern_rows = [
            {k: v["value"] for k, v in b.items() if k != "mandato"}
            for b in data["results"]["bindings"]
            if "/dd" not in b["sameAs"]["value"]
        ]
        assert len(modern_rows) == 4  # 5 total - 1 dd
        for row in modern_rows:
            link = extract_sameas_camera_link(row)
            assert link is not None
            sen_id, cam_id = link
            assert sen_id.isdigit()
            assert cam_id.startswith("d") and cam_id[1].isdigit()

    def test_parsers_and_extractor_are_consistent(self) -> None:
        """extract_sameas_camera_link must use the same regex semantics
        as parse_senato_person_id and parse_camera_person_id.
        """
        row = {
            "sen": "http://dati.senato.it/senatore/22918",
            "sameAs": "http://dati.camera.it/ocd/deputato.rdf/d301569_15",
        }
        link = extract_sameas_camera_link(row)
        assert link is not None
        sen_id, cam_id = link
        assert parse_senato_person_id(row["sen"]) == sen_id
        parsed = parse_camera_person_id(row["sameAs"])
        assert parsed is not None
        assert parsed[0] == cam_id
