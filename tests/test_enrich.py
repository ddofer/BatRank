from types import SimpleNamespace

from scripts.enrich import (
    appearance_entities,
    collection_targets,
    enrich_issue,
    indexed_credits,
    select_substories,
    team_features,
)


def test_named_backup_does_not_receive_first_story_creators():
    fields = {
        "StoryTitle1": "Death Casts the Deciding Vote",
        "StoryTitle2": "The Silent Night of the Batman",
        "Writer1_1": "Frank Robbins",
        "Writer2_1": "Mike Friedrich",
        "Penciler2_1": "Neal Adams",
        "Appearing1": "'''Featured Characters:'''\n* {{a|[[Bruce Wayne (Earth-One)|Batman]]}}",
        "Appearing2": "'''Supporting Characters:'''\n* {{a|[[James Gordon (Earth-One)|Gordon]]}}",
    }
    story = SimpleNamespace(story_id="silent", title="The Silent Night of the Batman")
    issue = SimpleNamespace(requested_title="Batman Vol 1 219")
    result = enrich_issue(story, issue, fields)
    assert result["selected_substory_indexes"] == "2"
    assert result["narrative_writers"] == "Mike Friedrich"
    assert result["featured_entity_ids"] is None
    assert result["supporting_entity_ids"] == "James Gordon (Earth-One)"


def test_ambiguous_issue_keeps_cast_scope_and_does_not_guess_credits():
    fields = {"StoryTitle1": "An unrelated main story", "StoryTitle2": "A second story"}
    assert select_substories("The arc name", fields) == ([], "ambiguous_whole_issue")
    assert (
        indexed_credits({**fields, "Writer1_1": "Wrong person"}, [], [1, 2])["narrative_writers"]
        is None
    )


def test_legacy_contributor_indexes_are_not_substory_indexes():
    fields = {"Writer1": "A", "Writer2": "B", "Penciler1_1": "C"}
    assert indexed_credits(fields, [1], [1])["narrative_writers"] == "A|B"
    assert indexed_credits(fields, [1], [1, 2])["narrative_writers"] is None


def test_role_modes_and_universes_are_preserved():
    rows = appearance_entities("""'''Featured Characters:'''
* {{a|[[Bruce Wayne (New Earth)|Batman]]}}
* {{A|[[Bruce Wayne (Earth-One)|Batman]]}} {{Flashback}}
'''Antagonists:'''
* {{a|[[Joker (New Earth)|Joker]]}} {{Mentioned}}
'''Locations:'''
* [[Gotham City]]
'''Items:'''
* [[Batsuit]]
""")
    assert [(r["id"], r["role"], r["mode"]) for r in rows] == [
        ("Bruce Wayne (New Earth)", "featured", "ordinary"),
        ("Bruce Wayne (Earth-One)", "featured", "flashback"),
        ("Joker (New Earth)", "antagonists", "mentioned"),
        ("Gotham City", "locations", "ordinary"),
    ]


def test_collection_links_only_come_from_notes_not_recommendations():
    fields = {
        "Notes": "Reprinted in {{Co|Batman: Year One (Collected)}} and [[Another (Collected)|another collection]].",
        "Recommended": "{{co|An unrelated book (Collected)}}",
    }
    assert collection_targets(fields, [1], 1) == [
        "Another (Collected)",
        "Batman: Year One (Collected)",
    ]


def test_unknown_issue_does_not_create_a_false_team_transition():
    def row(writer=None, artist=None, inker=None):
        return {
            "narrative_writers": writer,
            "narrative_pencilers": artist,
            "narrative_inkers": inker,
        }

    result = team_features([row("A", "B", "B"), row(), row("C", "C", "D")], 3)
    assert result["narrative_team_count"] == 2
    assert result["narrative_credit_issue_coverage"] == 2 / 3
    assert result["narrative_team_comparable_transitions"] == 0
    assert result["narrative_team_switch_count"] is None
    assert result["narrative_self_inking_share"] == 0.5
    assert result["narrative_writer_artist_overlap_share"] == 0.5


def test_untitled_story_with_indexed_credits_and_appearance_is_not_missing():
    fields = {
        "StoryTitle1": "",
        "Writer1_1": "Sean Murphy",
        "Appearing1": "'''Featured Characters:'''\n* [[Bruce Wayne (White Knight)|Batman]]",
    }
    assert select_substories("White Knight", fields) == ([1], "single_substory")


def test_flashalso_is_present_and_flashback_and_parent_modes_are_inherited():
    rows = appearance_entities("""'''Featured Characters:'''
* [[Bruce Wayne (New Earth)|Batman]] {{Flashalso}}
'''Other Characters:'''
* [[Wayne Family]] {{Mentioned}}
** [[Thomas Wayne (New Earth)|Thomas]]
* [[James Gordon (New Earth)|Gordon]]
""")
    bruce = [r["mode"] for r in rows if r["id"].startswith("Bruce")]
    assert bruce == ["ordinary", "flashback"]
    assert next(r for r in rows if r["id"].startswith("Thomas"))["mode"] == "mentioned"
    assert next(r for r in rows if r["id"].startswith("James"))["mode"] == "ordinary"


def test_placeholder_headers_do_not_count_as_cast_coverage():
    result = enrich_issue(
        SimpleNamespace(story_id="x", title="x"),
        SimpleNamespace(requested_title="x"),
        {"StoryTitle1": "x", "Appearing1": "'''Featured Characters:'''\n* "},
    )
    assert result["appearance_indexed_sections"] == 0
    assert result["ordinary_cast_entity_count"] is None


def test_no_colorist_is_not_a_person_and_short_title_does_not_match_word_fragment():
    assert indexed_credits({"Colorist1_1": "N/A"}, [1], [1])["narrative_colorists"] is None
    assert select_substories(
        "The Cat", {"StoryTitle1": "The Cathedral is on Fire", "StoryTitle2": "Other Story"}
    ) == ([], "ambiguous_whole_issue")


def test_anthology_self_inking_does_not_cross_assign_substory_credits():
    fields = {
        "StoryTitle1": "First narrative",
        "StoryTitle2": "Second narrative",
        "Writer1_1": "Writer A",
        "Writer2_1": "Writer B",
        "Penciler1_1": "Artist A",
        "Inker1_1": "Artist B",
        "Penciler2_1": "Artist B",
        "Inker2_1": "Artist A",
    }
    result = enrich_issue(
        SimpleNamespace(story_id="x", title="An anthology"),
        SimpleNamespace(requested_title="x"),
        fields,
        "all",
    )
    assert team_features([result], 1)["narrative_self_inking_share"] == 0


def test_whole_issue_selection_excludes_production_gallery():
    assert select_substories(
        "The issue",
        {
            "StoryTitle1": "A real narrative",
            "StoryTitle2": "Pinups",
            "StoryTitle3": "Batman: The Return Pencils to Inks Comparison",
        },
        "all",
    ) == ([1], "reviewed_override")


def test_real_battle_for_cowl_headings_without_colons():
    rows = appearance_entities("""'''Featured Characters'''
* {{a|[[Richard Grayson (New Earth)|Nightwing]]}} {{green|Return as Batman}}
'''Villains'''
* {{a|[[Jason Todd (New Earth)|Batman (Jason Todd)]]}} {{ApDeath}}
'''Items:'''
* {{a|[[Batsuit]]}}
""")
    assert [(r["id"], r["role"]) for r in rows] == [
        ("Richard Grayson (New Earth)", "featured"),
        ("Jason Todd (New Earth)", "antagonists"),
    ]


def test_real_kingdom_come_annotation_links_are_not_cast_entities():
    rows = appearance_entities("""'''Supporting Characters:'''
* {{a|[[Bulletgirl (Earth-22)|Bulletgirl]]}} {{Unnamed}} {{ApDeath}} {{Green|[[The Kingdom Vol 1 1#alive|See Notes]]}}
""")
    assert [r["id"] for r in rows] == ["Bulletgirl (Earth-22)"]


def test_real_action_comics_qualifier_text_is_parsed_without_adding_comic_to_cast():
    rows = appearance_entities("""'''Antagonists:'''
* {{A|[[Alexander Luthor (New Earth)|Lex Luthor]]}} {{green|[[Superman Vol 2 2|Flashback Only]]}}
'''Other Characters:'''
* {{A|[[Matthew Sockton (New Earth)|Matt Stockton]]}} {{green|[[Superman Vol 2 28|Flashback Only, dies]]}}
""")
    assert [(r["id"], r["mode"]) for r in rows] == [
        ("Alexander Luthor (New Earth)", "flashback"),
        ("Matthew Sockton (New Earth)", "flashback"),
    ]


def test_hero_themed_waiters_and_vision_character_names_do_not_confuse_parser():
    rows = appearance_entities("""'''Other Characters:'''
* [[Aquaman]]-themed waiter {{Unnamed}}
* {{a|[[Vision (New Earth)|Vision]]}}
""")
    assert [(r["id"], r["mode"]) for r in rows] == [("Vision (New Earth)", "ordinary")]


def test_anthology_writer_artist_overlap_is_within_same_substory():
    fields = {
        "StoryTitle1": "First narrative",
        "StoryTitle2": "Second narrative",
        "Writer1_1": "Creator A",
        "Penciler1_1": "Creator B",
        "Writer2_1": "Creator B",
        "Penciler2_1": "Creator A",
    }
    result = enrich_issue(
        SimpleNamespace(story_id="x", title="An anthology"),
        SimpleNamespace(requested_title="x"),
        fields,
        "all",
    )
    assert team_features([result], 1)["narrative_writer_artist_overlap_share"] == 0


def test_locations_alone_do_not_supply_character_coverage():
    result = enrich_issue(
        SimpleNamespace(story_id="x", title="x"),
        SimpleNamespace(requested_title="x"),
        {
            "StoryTitle1": "x",
            "Appearing1": "'''Featured Characters:'''\n* \n'''Locations:'''\n* [[Gotham City]]",
        },
    )
    assert result["appearance_indexed_sections"] == 0
    assert result["ordinary_cast_entity_count"] is None
    assert result["locations_entity_ids"] == "Gotham City"
