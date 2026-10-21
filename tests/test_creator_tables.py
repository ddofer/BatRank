import pandas as pd
import pytest

from scripts.creator_tables import (
    alias_index,
    build_tables,
    canonical_name,
    creator_id,
    extend_award_audit,
)


def issue(title, *, writers=None, publication_year=None, cover_year=None, **extra):
    return {
        "story_id": "story",
        "requested_title": title,
        "wiki_title": title,
        "issue_id": int(title.rsplit(" ", 1)[-1]),
        "writers": writers,
        "publication_year": publication_year,
        "cover_year": cover_year,
        **extra,
    }


def event(event_id, *, scope="personal", names=None, award="Eisner", year=2000):
    return {
        "event_id": event_id,
        "award": award,
        "award_year": year,
        "category": "Hall of Fame" if scope == "honor" else "Best Writer/Artist",
        "recipient_scope": scope,
        "recipient_names": names or [],
        "winning_roles": ["writers", "pencilers"],
        "awarded_work": "An awarded work",
        "source_url": "https://example.org/official-winners",
    }


def build(rows, events=None, aliases=None):
    return build_tables(
        pd.DataFrame([{"story_id": "story"}]),
        pd.DataFrame(rows),
        {"events": events or [], "award_years": [1985, 2025]},
        aliases=aliases,
    )


def test_known_spellings_merge_but_raw_variants_and_credit_scope_survive():
    creators, credits, _, _ = build(
        [
            issue(
                "Comic 1",
                writers="Dave Mazzucchelli|David Mazzucchelli",
                narrative_writers="David Mazzucchelli",
                cover_artists="Dave Mazzucchelli",
            ),
            issue("Comic 2", writers="Dave Mazzucchelli"),
        ]
    )
    assert len(creators) == 1
    assert creators.iloc[0]["name"] == "Dave Mazzucchelli"
    assert creators.iloc[0].credit_name_variants == "Dave Mazzucchelli|David Mazzucchelli"
    assert creators.iloc[0].entity_type == "unresolved"
    assert set(zip(credits.role, credits.credit_scope)) == {
        ("writers", "whole_issue"),
        ("writers", "selected_narrative"),
        ("cover_artists", "whole_issue"),
    }
    assert (
        credits.query('role == "writers" and credit_scope == "whole_issue"').reference_count.iloc[0]
        == 2
    )
    assert creator_id("David Mazzucchelli") == creator_id("Dave Mazzucchelli")


def test_placeholder_names_are_removed_and_audited_without_human_type_guessing():
    creators, _, _, report = build(
        [issue("Comic 1", writers="N/A|Unknown|None|Various|h1|h2|Digital Chameleon")]
    )
    assert creators.name.tolist() == ["Digital Chameleon"]
    assert creators.entity_type.tolist() == ["unresolved"]
    assert report["excluded_placeholder_occurrences"] == 6


def test_creator_role_clock_uses_only_that_creators_contributing_references():
    _, credits, _, _ = build(
        [
            issue("Comic 1", writers="Early Writer", publication_year=1986, cover_year=1987),
            issue("Comic 2", writers="Early Writer", publication_year=None, cover_year=1988),
            issue("Comic 3", writers="Late Writer", publication_year=2000, cover_year=2001),
            issue(
                "Comic 4",
                writers="Early Writer",
                publication_year=2009,
                cover_year=2010,
                narrative_writers="Late Writer",
            ),
        ]
    )
    late = credits[
        (credits.creator_id == creator_id("Late Writer")) & credits.credit_scope.eq("whole_issue")
    ].iloc[0]
    assert late.publication_year_proxy == late.publication_year_end_proxy == 2000
    assert late.year_basis == "actual_publication_year"
    early = credits[
        (credits.creator_id == creator_id("Early Writer")) & credits.credit_scope.eq("whole_issue")
    ].iloc[0]
    assert early.publication_year_proxy == 1987 and early.publication_year_end_proxy == 2010
    assert early.year_basis == "cover_year_proxy"
    assert early.actual_publication_year_reference_count == 2
    late_narrative = credits[
        (credits.creator_id == creator_id("Late Writer"))
        & credits.credit_scope.eq("selected_narrative")
    ].iloc[0]
    assert late_narrative.publication_year_proxy == 2009


def test_clock_does_not_mix_partial_actual_years_with_partial_cover_years():
    _, credits, _, _ = build(
        [
            issue("Comic 1", writers="A", publication_year=1986, cover_year=None),
            issue("Comic 2", writers="A", publication_year=None, cover_year=1988),
        ]
    )
    assert credits.iloc[0].year_basis == "unknown"
    assert pd.isna(credits.iloc[0].publication_year_proxy)


def test_personal_event_counts_are_distinct_and_work_awards_never_become_personal():
    events = [
        event("personal", names=["Dave Mazzucchelli", "David Mazzucchelli"]),
        event("kirby", names=["David Mazzucchelli"], award="Kirby", year=1987),
        event("fame", names=["David Mazzucchelli"], scope="honor"),
        event("work", names=["David Mazzucchelli"], scope="work"),
    ]
    creators, _, awards, _ = build(
        [issue("Comic 1", writers="Dave Mazzucchelli", pencilers="Dave Mazzucchelli")],
        events + [events[0]],
    )
    assert len(awards) == 3
    row = creators.iloc[0]
    assert row.eisner_personal_win_count_observed == 1
    assert row.kirby_personal_win_count_observed == 1
    assert row.hall_of_fame_event_count_observed == 1
    assert set(row.award_event_ids_observed.split("|")) == {"personal", "kirby", "fame"}


def test_reviewed_aliases_are_consistent_across_credits_and_awards():
    aliases = {"Joe Rubinstein": "Josef Rubinstein"}
    creators, _, awards, _ = build(
        [issue("Comic 1", writers="Joe Rubinstein|Josef Rubinstein")],
        [event("win", names=["Joe Rubinstein"])],
        aliases,
    )
    assert creators.name.tolist() == ["Josef Rubinstein"]
    assert len(awards) == 1
    assert canonical_name("Joe Rubinstein", aliases) == "Josef Rubinstein"
    assert creator_id("Joe Rubinstein", aliases) == creator_id("Josef Rubinstein", aliases)


def test_alias_cycles_and_normalized_conflicts_fail_loudly():
    with pytest.raises(ValueError, match="Cyclic"):
        canonical_name("A", {"A": "B", "B": "A"})
    with pytest.raises(ValueError, match="Conflicting normalized"):
        canonical_name("A", {"A.": "B", "A": "C"})
    with pytest.raises(ValueError, match="Ambiguous"):
        alias_index({"Person A": ["Shared Alias"], "Person B": ["Shared Alias"]})
    assert canonical_name("A", {"A": "B", "B": "C"}) == "C"


def test_award_audit_refreshes_recipients_and_retains_work_records():
    events = [
        event("old", names=["Existing", "New Cover Artist"]),
        event("new", names=["New Cover Artist"]),
        event("work", scope="work"),
    ]
    existing = pd.DataFrame(
        [
            {"event_id": "old", "recipient_names": "Existing"},
            {"event_id": "work", "recipient_names": ""},
        ]
    )
    linked = pd.DataFrame(
        [{"creator_id": "creator", "event_id": "old"}, {"creator_id": "creator", "event_id": "new"}]
    )
    audit = extend_award_audit(existing, {"events": events}, linked).set_index("event_id")
    assert set(audit.index) == {"old", "new", "work"}
    assert audit.loc["old", "recipient_names"] == "Existing|New Cover Artist"
    assert audit.loc["work", "recipient_scope"] == "work"


def test_canonical_reference_aliases_do_not_inflate_reference_count():
    first = issue("Comic 1", writers="A", publication_year=2000, cover_year=2001)
    second = {**first, "requested_title": "Other label 1"}
    _, credits, _, _ = build([first, second])
    assert credits.iloc[0].reference_count == 1
    bad = {**second, "cover_year": 2002}
    with pytest.raises(ValueError, match="Conflicting cover_year"):
        build([first, bad])


def test_award_ids_cannot_refer_to_conflicting_events():
    a = event("same", names=["A"])
    b = {**a, "award_year": 2020}
    with pytest.raises(ValueError, match="Conflicting award event"):
        build([issue("Comic 1", writers="A")], [a, b])


def test_duplicate_reference_coalesces_known_year_without_counting_twice():
    first = issue("Comic 1", writers="A", publication_year=None, cover_year=2001)
    second = {**first, "requested_title": "Alias 1", "publication_year": 2000}
    _, credits, _, _ = build([first, second])
    assert credits.iloc[0].reference_count == 1
    assert credits.iloc[0].year_basis == "actual_publication_year"
    assert credits.iloc[0].publication_year_proxy == 2000


def test_empty_or_placeholder_alias_targets_are_rejected():
    with pytest.raises(ValueError, match="nonempty names"):
        canonical_name("A", {"A": ""})
    with pytest.raises(ValueError, match="non-placeholder"):
        canonical_name("A", {"A": "N/A"})
