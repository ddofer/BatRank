import pandas as pd

from scripts import awards


def test_archive_heading_and_two_winners_in_one_item():
    html = """<div class="entry-content"><h5>2002 Eisner Awards for works published in 2001</h5>
    <ul><li><strong>Best Continuing Series:</strong> 100 Bullets, by A and B (DC)
    Best Limited Series: Hellboy, by Mike Mignola (Dark Horse)</li>
    <li>Best Writer: Brian Michael Bendis, <em>Daredevil</em> (Marvel)</li></ul></div>"""
    events, years = awards.parse_winners(
        html, "https://example.test/winners", {"brianmichaelbendis": "Brian Michael Bendis"}
    )
    assert years == [2002]
    assert len(events) == 3
    assert events[1]["category"] == "Best Limited Series"
    assert events[2]["recipient_scope"] == "personal"
    assert events[2]["recipient_names"] == ["Brian Michael Bendis"]
    assert events[0]["recipient_names"] == []


def test_split_list_item_and_tied_recipients():
    html = """<div class="entry-content"><h2>2005 Eisner Awards for works published in 2004</h2>
    <ul><li>Best Archival Collection/Project—Strips:</li><li><em>Peanuts</em>, by Charles Schulz</li>
    <li>Best Penciller/Inker (tie): John Cassaday, <em>Planetary</em> (DC); and Frank Quitely, <em>WE3</em> (DC)</li>
    <li>Best Editor (tie): Karen Berger, <em>Sandman</em> (DC) and Mike Carlin, Superman titles (DC)</li></ul></div>"""
    index = {
        awards.normalize(name): name
        for name in [
            "John Cassaday",
            "Frank Quitely",
            "Karen Berger",
            "Mike Carlin",
            "Charles Schulz",
        ]
    }
    events, _ = awards.parse_winners(html, "https://example.test/winners", index)
    assert len(events) == 3
    assert events[0]["awarded_work"].startswith("Peanuts")
    assert events[1]["recipient_names"] == ["Frank Quitely", "John Cassaday"]
    assert events[2]["recipient_names"] == ["Karen Berger", "Mike Carlin"]


def test_creator_names_are_not_award_work_creators():
    html = """<div class="entry-content"><h2>2025 Eisner Awards for works published in 2024</h2><ul>
    <li>Best Coloring: Jordie Bellaire, <em>Batman</em> (DC)</li>
    <li>Best Limited Series: Batman, by Frank Miller (DC)</li>
    <li>Hall of Fame: Frank Miller, Jordie Bellaire</li></ul></div>"""
    events, _ = awards.parse_winners(
        html,
        "https://example.test/winners",
        {"jordiebellaire": "Jordie Bellaire", "frankmiller": "Frank Miller"},
    )
    assert events[0]["recipient_names"] == ["Jordie Bellaire"]
    assert events[0]["winning_roles"] == ["colorists"]
    assert events[1]["recipient_names"] == []
    assert events[1]["recipient_scope"] == "work"
    assert events[2]["recipient_scope"] == "honor"


def test_normalization_does_not_match_substrings():
    index = {"davidmazzucchelli": "Dave Mazzucchelli", "timsale": "Tim Sale"}
    assert awards.match_creators("David Mazzucchelli and Timothy Sales", index) == [
        "Dave Mazzucchelli"
    ]
    assert awards.normalize("José Marzán, Jr.") == awards.normalize("Jose Marzan Jr")


def test_temporal_counts_scope_and_not_started_are_explicit(monkeypatch):
    monkeypatch.setattr(awards, "WORK_MATCHES", [])
    rows = []
    for story_id, publication in [("old", 1987), ("same", 2010), ("later", 2011)]:
        rows.append(
            dict(
                story_id=story_id,
                publication_year_start=publication,
                cover_year_start=publication,
                discussion_date="2021-09-01",
                **{
                    role: "Todd Klein"
                    if role == "letterers"
                    else "Frank Miller"
                    if role == "writers"
                    else None
                    for role in awards.ROLES
                },
            )
        )
    events = [
        dict(
            event_id="one",
            award="Eisner",
            award_year=2010,
            recipient_scope="personal",
            recipient_names=["Frank Miller"],
            winning_roles=["writers"],
        ),
        dict(
            event_id="future",
            award="Eisner",
            award_year=2022,
            recipient_scope="personal",
            recipient_names=["Todd Klein"],
            winning_roles=["letterers"],
        ),
    ]
    result = awards.enrich(pd.DataFrame(rows), events)
    assert result["old"]["creator_eisner_personal_wins_pre_publication"] is None
    assert result["same"]["creator_eisner_personal_wins_pre_publication"] == 0
    assert result["later"]["creator_eisner_personal_wins_pre_publication"] == 1
    assert result["later"]["creator_eisner_personal_wins_pre_discussion"] == 1
    assert result["later"]["creator_eisner_personal_wins_after_discussion_year"] == 1
    assert result["later"]["work_awards_match_status"] == "not_exhaustively_reviewed"
    narrative = {
        "later": dict(
            substory_attribution_coverage=1,
            narrative_credit_issue_coverage=1,
            narrative_writers="Someone Else",
        )
    }
    selected = awards.enrich(pd.DataFrame(rows), events, narrative)
    assert selected["later"]["awards_credit_scope"] == "selected_narratives"
    assert selected["later"]["creator_eisner_personal_wins_total"] == 0


def test_partial_publication_dates_use_cover_proxy_and_later_edition_stays_later(monkeypatch):
    monkeypatch.setattr(
        awards,
        "WORK_MATCHES",
        [("one", 2025, "Best Publication Design", "edition_design", "Archival edition design.")],
    )
    stories = pd.DataFrame(
        [
            dict(
                story_id="one",
                publication_year_start=2001,
                cover_year_start=2000,
                discussion_date="2021-09-01",
                **{role: "Frank Miller" if role == "writers" else None for role in awards.ROLES},
            )
        ]
    )
    events = [
        dict(
            event_id="person",
            award="Eisner",
            award_year=2000,
            recipient_scope="personal",
            recipient_names=["Frank Miller"],
            winning_roles=["writers"],
        ),
        dict(
            event_id="edition",
            award="Eisner",
            award_year=2025,
            category="Best Publication Design",
            recipient_scope="work",
            recipient_names=[],
            winning_roles=[],
        ),
    ]
    row = awards.enrich(stories, events, complete_publication_years={})["one"]
    assert row["awards_publication_year_basis"] == "cover_year_proxy"
    assert row["creator_eisner_personal_wins_pre_publication"] == 0
    assert row["work_eisner_edition_design_wins"] == 1
    assert row["work_eisner_exact_work_wins_pre_discussion"] == 0
    assert row["work_eisner_matched_wins_after_discussion_year"] == 1


def test_personal_recipient_index_excludes_verified_studio_affiliations(monkeypatch, tmp_path):
    import json

    (tmp_path / "references").mkdir()
    (tmp_path / "references/creator_entity_types.json").write_text(
        json.dumps({"Olyoptics": {"entity_type": "organization"}})
    )
    monkeypatch.setattr(awards, "ROOT", tmp_path)
    stories = pd.DataFrame(
        [{role: "Steve Oliff|Olyoptics" if role == "colorists" else None for role in awards.ROLES}]
    )
    index = awards.creator_index(stories)
    assert "steveoliff" in index
    assert "olyoptics" not in index
    html = '<div class="entry-content"><h2>1994 Eisner Awards</h2><ul><li>Best Colorist: Steve Oliff and Reuben Rude (Olyoptics), <em>Spawn</em></li></ul></div>'
    events, _ = awards.parse_winners(html, "https://example.test", index)
    assert events[0]["recipient_names"] == ["Steve Oliff"]
