import json

import pytest

from scripts.dataset import clean, issue_titles, parse_issue, parse_rankings


def test_source_rank_errors_and_split_links_preserve_every_story():
    html = """<div class="entry-content"><p>
    <a href="https://comicsxf.com/2021/09/23/a/">1. First (Batman V.1 #1)</a><br>
    <a href="https://comicsxf.com/2022/01/01/b/">1</a><a href="b">. Second</a><br>
    <a href="https://comicsxf.com/2023/01/01/c/">3. Third</a><a href="https://comicsxf.com/2024/01/01/d/">
    4. Fourth</a></p></div>"""
    rows = parse_rankings(html)
    assert [r["source_rank"] for r in rows] == [1, 1, 3, 4]
    assert [r["rank"] for r in rows] == [1, 2, 3, 4]
    assert rows[1]["rank_label_disagrees"]
    assert rows[-1]["discussion_date"] == "2024-01-01"


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Batman V.3 #51-53", ["Batman Vol 3 51", "Batman Vol 3 52", "Batman Vol 3 53"]),
        ("Batman/Superman V.1 #1-2", ["Batman/Superman Vol 1 1", "Batman/Superman Vol 1 2"]),
        (
            "Batman V.1 #1,3, Annual #2",
            ["Batman Vol 1 1", "Batman Vol 1 3", "Batman Annual Vol 1 2"],
        ),
        ("Batman V.2 #23.2", ["Batman Vol 2 23.2"]),
        ("Zero Hour #4-0", [f"Zero Hour Vol 1 {n}" for n in range(4, -1, -1)]),
        (
            "Batman V.1 #232,235,240,242-244",
            [f"Batman Vol 1 {n}" for n in [232, 235, 240, 242, 243, 244]],
        ),
        ("Batman #1,000,000", ["Batman Vol 1 1000000"]),
    ],
)
def test_issue_reference_expansion(label, expected):
    assert issue_titles(label) == (expected, True)


def test_missing_unparsed_and_maliciously_large_ranges():
    assert not issue_titles("Batman #1-3, another unnamed book")[1]
    with pytest.raises(ValueError):
        issue_titles("Batman #1-99999")
    assert parse_issue({"missing": ""}) == {}
    assert (
        clean("[[File:cover.jpg|thumb|Caption]] [[Bruce Wayne|Batman]] <!-- note -->") == "Batman"
    )


def test_credit_roles_do_not_mix_and_templates_are_stripped():
    text = """{{DC Database:Comic Template|Year=1987|Pubyear=1986<!-- GCD -->
    |Writer1_1=[[Frank Miller]]|Penciler1_1=Dave Mazzucchelli|Editor1_1=Dennis O'Neil
    |Executive Editor=Dick Giordano|StoryTitle1=Chapter One}}"""
    page = {
        "title": "Batman Vol 1 404",
        "pageid": 12098,
        "fullurl": "https://dc.fandom.com/wiki/Batman_Vol_1_404",
        "revisions": [
            {"revid": 123, "timestamp": "2026-01-01T00:00:00Z", "slots": {"main": {"*": text}}}
        ],
    }
    data = parse_issue(page)
    assert data["writers"] == "Frank Miller"
    assert data["editors"] == "Dennis O'Neil"
    assert data["executive_editors"] == "Dick Giordano"
    assert data["publication_year"] == "1986"
    assert json.dumps(data)


def test_offline_cache_rebuilds_from_raw_with_redirects(tmp_path, monkeypatch):
    from scripts import dataset

    raw = tmp_path / "data/raw"
    raw.mkdir(parents=True)
    page = {"title": "Canonical", "pageid": 1}
    (raw / "batch.json").write_text(
        json.dumps(
            {
                "query": {
                    "pages": {"1": page},
                    "normalized": [{"from": "An_Alias", "to": "An Alias"}],
                    "redirects": [{"from": "An Alias", "to": "Canonical"}],
                }
            }
        )
    )
    monkeypatch.setattr(dataset, "ROOT", tmp_path)
    monkeypatch.setattr(dataset, "RAW", raw)
    assert dataset.wiki_pages(dataset.Fetcher(offline=True), ["An_Alias"]) == {"An_Alias": page}


def test_enrichment_rejects_stale_reading_lists_and_preserves_structured_provenance():
    import json
    import pandas as pd
    import pytest
    from scripts.dataset import attach_snapshot

    stories = pd.DataFrame([{"story_id": "a", "title": "Museum of Mixed-Up Men"}])
    issues = pd.DataFrame([{"story_id": "a", "requested_title": "Detective Comics Vol 1 331"}])
    extra = {
        "stories": {"a": {"provenance": [{"source": "GCD"}]}},
        "issues": [
            {
                "story_id": "a",
                "requested_title": "Detective Comics Vol 1 313",
                "cast": "wrong issue",
            }
        ],
    }
    with pytest.raises(AssertionError, match="Stale"):
        attach_snapshot(stories, issues, extra)
    extra["issues"][0]["requested_title"] = "Detective Comics Vol 1 331"
    attached, refs = attach_snapshot(stories, issues, extra)
    assert json.loads(attached.provenance.iloc[0]) == [{"source": "GCD"}]
    assert len(refs) == 1 and attached.title.iloc[0] == "Museum of Mixed-Up Men"


def test_rating_scope_distinguishes_a_backup_from_whole_issue():
    import pandas as pd
    from scripts.dataset import narrative_rating_scope

    refs = pd.DataFrame(
        {
            "selected_substory_indexes": ["1", "2", "1|2", None],
            "indexed_substory_count": [1, 3, 2, 2],
        }
    )
    assert narrative_rating_scope(refs).tolist() == [
        "all_indexed_narratives",
        "ranked_subset_of_issue",
        "all_indexed_narratives",
        "unresolved_issue_scope",
    ]
