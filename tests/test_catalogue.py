import json

import pytest

from scripts import catalogue


def record(body, issue=123):
    return f"GCD :: Issue :: Example (DC, 2000 series) #1 (https://www.comics.org/issue/{issue}/)\n[search citation] [wordlim: 200] comic story / 999 pages\n\n{body}"


def test_narrative_pages_are_not_physical_pages_or_cover_pages():
    text = record("""Pages: 36
On-sale Date: 2000-01-19

Cover

(Table of Contents)

###

Batman / cover / 1 page

Actual story

(Table of Contents: 1)

###

Batman / comic story / 14.17 pages

Script:  | Example Writer (credited)
Pencils:  | Example Artist

Backup

(Table of Contents: 2)

###

Batman / text story / 8 pages
""")
    rows = catalogue.parse_records(text)
    assert len(rows) == 2
    assert rows[0]["narrative_page_count"] == 14.17
    assert rows[0]["physical_issue_page_count"] == 36
    assert rows[0]["on_sale_date"] == "2000-01-19"
    assert rows[0]["credit_strings"] == {
        "Script": "Example Writer (credited)",
        "Pencils": "Example Artist",
    }
    assert rows[1]["narrative_type"] == "text story"


def test_clipped_search_text_is_not_attached_to_wrong_title():
    text = record("""Introduction

(Table of Contents: 1)

This is a clipped introduction. Later another story appears:

Batman / comic story / 22 pages
""")
    assert catalogue.parse_records(text) == []


def test_duplicate_views_keep_more_complete_same_issue_record():
    body = """Story

(Table of Contents: 1)

###

Batman / comic story / 20 pages
"""
    text = record(body) + "\n" + "-" * 80 + "\n" + record(body + "\nScript:  | Writer\n")
    rows = catalogue.parse_records(text)
    assert len(rows) == 1
    assert rows[0]["credit_strings"]["Script"] == "Writer"


def test_sample_is_exact_scoped_and_complete_totals_are_honest():
    data = json.loads((catalogue.ROOT / "data/external/catalogue.json").read_text())
    rows = {r["story_id"]: r for r in data["stories"]}
    assert rows["c1754cfe9f72"]["gcd_narrative_page_count"] == 90
    assert rows["806af1982441"]["gcd_narrative_page_count"] == 22.17
    assert rows["191befd05358"]["gcd_narrative_page_count"] is None
    assert rows["435e0299004d"]["gcd_sampled_narrative_page_count"] == 8
    assert rows["435e0299004d"]["gcd_reference_coverage"] == 1 / 16
    assert rows["f8770a6ab230"]["gcd_narrative_page_count"] is None
    reprints = [r for r in data["records"] if r["match_scope"] == "same_story_reprint"]
    assert reprints
    assert all(
        r["on_sale_date"] is None and r["physical_issue_page_count"] is None for r in reprints
    )


def test_unknown_issue_identity_is_rejected(tmp_path, monkeypatch):
    sample = record("Story\n\n(Table of Contents: 1)\n\n###\n\nBatman / comic story / 20 pages\n")
    (tmp_path / "sample.txt").write_text(sample)
    (tmp_path / "matches.json").write_text(
        json.dumps(
            [
                {
                    "snapshot_file": "sample.txt",
                    "catalogue_issue_id": 123,
                    "catalogue_sequence": 1,
                    "narrative_title": "Story",
                    "expected_issue": "Entirely Different Comic",
                }
            ]
        )
    )
    monkeypatch.setattr(catalogue, "RAW", tmp_path)
    with pytest.raises(ValueError, match="Issue identity mismatch"):
        catalogue.build()


def test_publisher_specs_keep_edition_and_narrative_distinct():
    text = """EXAMPLE | DC (https://www.dc.com/graphic-novels/example)
L0: # EXAMPLE
L1: ### Talent
L2: Written by:
L3: cite2†First Writer L4: cite3†Second Writer
L5: Art by:
L6: cite4†Various L7: cite5†Artist Name
L8: ### SPECS
L9: On Sale Date:
L10: Wednesday, December 3rd, 2014
L11: Page Count:
L12: 352
"""
    result = catalogue.parse_publisher(text)
    assert result["publisher_writers"] == "First Writer; Second Writer"
    assert result["publisher_artists"] == "Artist Name"
    assert result["publisher_edition_on_sale_date"] == "2014-12-03"
    assert result["publisher_physical_page_count"] == 352
    assert "gcd_narrative_page_count" not in result
    with pytest.raises(ValueError, match="Missing publisher"):
        catalogue.parse_publisher(text.replace("Page Count:", "Unavailable:"))


def test_publisher_anthology_is_not_transferred_as_ranked_story_length():
    data = json.loads((catalogue.ROOT / "data/external/catalogue.json").read_text())
    stories = {row["story_id"]: row for row in data["stories"]}
    assert stories["302bcc15a310"]["publisher_physical_page_count"] == 112
    draining = stories["75c0649b684d"]
    assert draining["publisher_match_scope"] == "contains_ranked_story"
    assert draining["publisher_physical_page_count"] == 264
    assert "gcd_narrative_page_count" not in draining
