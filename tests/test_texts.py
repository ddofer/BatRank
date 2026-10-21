import pandas as pd

from scripts.texts import build_texts, plain_synopsis


def page(title, fields, *, page_id=1, revision=101):
    text = (
        "{{DC Database:Comic Template\n"
        + "\n".join(f"| {key} = {value}" for key, value in fields.items())
        + "\n}}"
    )
    return {
        "title": title,
        "pageid": page_id,
        "fullurl": f"https://dc.fandom.com/wiki/{title.replace(' ', '_')}",
        "revisions": [
            {"revid": revision, "timestamp": "2026-10-21T10:00:00Z", "slots": {"main": {"*": text}}}
        ],
    }


def issue(title="Comic 1", indexes="1", *, story_id="story", issue_id=1):
    return {
        "story_id": story_id,
        "requested_title": title,
        "lookup_title": title,
        "wiki_title": title,
        "issue_id": issue_id,
        "selected_substory_indexes": indexes,
    }


def build(issues, pages, complete=True):
    stories = pd.DataFrame(
        [
            {"story_id": key, "issue_list_complete": complete}
            for key in dict.fromkeys(row["story_id"] for row in issues)
        ]
    )
    return build_texts(stories, pd.DataFrame(issues), pages)


def test_full_synopsis_is_not_truncated():
    long_plot = "Batman follows the clues through Gotham. " * 200
    table, _ = build(
        [issue()], {"Comic 1": page("Comic 1", {"StoryTitle1": "A story", "Synopsis1": long_plot})}
    )
    assert table.iloc[0].synopsis_text == long_plot.strip()
    assert len(table.iloc[0].synopsis_text) > 1200
    assert table.iloc[0].synopsis_word_count == len(long_plot.split())


def test_reception_section_is_removed_without_removing_plot_or_later_plot_sections():
    assert (
        plain_synopsis(
            "Batman visits the reception desk.\n\n==Reception==\nIGN ranked this fourth.\n"
            "===Critical reception===\nFive stars.\n===Reviews===\nCritics loved it.\n"
            "==Epilogue==\nRobin comes home."
        )
        == "Batman visits the reception desk.\n\nEpilogue Robin comes home."
    )
    assert plain_synopsis("Plot.\n==Critical reception==\nFive stars.") == "Plot."


def test_anthology_credit_headers_removed_but_metafiction_kept():
    text = (
        "Five [[Batman]] stories by some of comics' top creators. Each story is accompanied "
        "with a one-page profile of the artist or artists who worked on it.\n"
        "==Legend==\n'''Writer:''' [[Walt Simonson]]<br />\n"
        "'''Artist:''' [[Walt Simonson]]<br />\n'''Synopsis:'''<br />\n"
        "Batman survives in legend.\n\n"
        "Bat-Mite visits writer Bob Rozakis and penciler Michael Golden."
    )
    result = plain_synopsis(text)
    assert "Walt Simonson" not in result and "one-page profile" not in result
    assert "Legend" in result and "Batman survives in legend." in result
    assert "writer Bob Rozakis and penciler Michael Golden" in result


def test_markup_and_nested_citations_are_removed_but_paragraphs_and_link_labels_remain():
    result = plain_synopsis(
        "<p>[[Bruce Wayne|Batman]] meets {{WP|Sherlock Holmes|Holmes}}.<ref name='book'>A citation with unrelated words.</ref></p><p>They find a clue. [[File:Clue.jpg|A caption]]</p>"
    )
    assert result == "Batman meets Holmes.\n\nThey find a clue."
    assert "citation" not in result
    assert "caption" not in result


def test_stub_templates_and_filler_are_not_false_plot_text():
    for value in [
        "{{Synopsis Needed}}",
        "{{Summary Needed}}",
        "{{expand}}",
        "The synopsis for this issue has not yet been written.",
        "Synopsis not yet written",
        "No synopsis yet.",
        "Synopsis coming soon.",
        "TBA",
        "<!-- Please add a synopsis -->",
    ]:
        assert plain_synopsis(value) is None, value
    assert plain_synopsis("Synopsis not yet written.\n\nBatman returns.") == "Batman returns."
    assert plain_synopsis("Batman dies.") == "Batman dies."


def test_selected_backup_does_not_receive_the_first_story_plot():
    table, _ = build(
        [issue(indexes="2")],
        {
            "Comic 1": page(
                "Comic 1",
                {
                    "StoryTitle1": "Unrelated story",
                    "Synopsis1": "An unrelated villain escapes.",
                    "StoryTitle2": "Selected backup",
                    "Synopsis2": "A detective solves the case.",
                },
            )
        },
    )
    assert len(table) == 1
    assert table.iloc[0].substory_index == 2
    assert table.iloc[0].substory_title == "Selected backup"
    assert table.iloc[0].synopsis_text == "A detective solves the case."


def test_unresolved_selection_produces_a_missing_row_without_guessing():
    table, report = build(
        [issue(indexes=None)],
        {
            "Comic 1": page(
                "Comic 1", {"StoryTitle1": "First story", "Synopsis1": "Batman solves this case."}
            )
        },
    )
    assert len(table) == 1 and pd.isna(table.iloc[0].substory_index)
    assert pd.isna(table.iloc[0].synopsis_text)
    assert table.iloc[0].text_status == "unresolved_substory_selection"
    assert report["stories_with_unresolved_substory_selection"] == 1
    assert report["stories_with_any_available_synopsis"] == 0


def test_explicit_cached_transclusion_preserves_actual_source_index_and_revision():
    pages = {
        "Comic 1": page(
            "Comic 1",
            {"StoryTitle2": "A reprinted story", "Synopsis2": "{{StoryGrab|Original Comic|3}}"},
        ),
        "Original Comic": page(
            "Original Comic",
            {"StoryTitle3": "The original story", "Synopsis3": "Robin rescues the detective."},
            page_id=9,
            revision=909,
        ),
    }
    table, report = build([issue(indexes="2")], pages)
    row = table.iloc[0]
    assert row.wiki_title == "Comic 1" and row.issue_id == 1
    assert row.substory_index == 2 and row.source_substory_index == 3
    assert row.source_url.endswith("Original_Comic")
    assert row.revision_id == 909 and row.revision_url.endswith("?oldid=909")
    assert row.synopsis_text == "Robin rescues the detective."
    assert report["cached_transclusion_rows"] == 1


def test_missing_transclusion_and_stale_selection_are_flagged():
    pages = {
        "Comic 1": page(
            "Comic 1", {"StoryTitle1": "A story", "Synopsis1": "{{StoryGrab|Uncached Comic|2}}"}
        )
    }
    missing, _ = build([issue()], pages)
    assert missing.iloc[0].text_status == "missing_cached_transclusion"
    stale, _ = build([issue(indexes="9")], pages)
    assert stale.iloc[0].text_status == "stale_selected_substory_index"


def test_cyclic_transclusion_does_not_recurse_forever():
    pages = {
        "Comic 1": page("Comic 1", {"Synopsis1": "{{StoryGrab|Comic 2|1}}"}),
        "Comic 2": page("Comic 2", {"Synopsis1": "{{StoryGrab|Comic 1|1}}"}),
    }
    table, _ = build([issue()], pages)
    assert table.iloc[0].text_status == "cyclic_cached_transclusion"


def test_coverage_requires_every_selected_text_and_a_known_complete_reading_list():
    pages = {
        "Comic 1": page("Comic 1", {"StoryTitle1": "First", "Synopsis1": "Batman returns."}),
        "Comic 2": page("Comic 2", {"StoryTitle1": "Second", "Synopsis1": ""}),
    }
    _, report = build([issue(), issue("Comic 2", issue_id=2)], pages)
    assert report["stories_with_any_available_synopsis"] == 1
    assert report["selected_rows_missing_clean_text"] == 1
    assert report["stories_all_selected_synopses_available_and_reading_list_complete"] == 0
    _, partial = build([issue()], pages, complete=False)
    assert partial["stories_all_selected_synopses_available_and_reading_list_complete"] == 0


def test_duplicate_source_narratives_are_reported_without_dropping_ranked_associations():
    pages = {"Comic 1": page("Comic 1", {"Synopsis1": "Batman solves the case."})}
    table, report = build([issue(story_id="a"), issue(story_id="b")], pages)
    assert len(table) == 2
    assert report["shared_source_narrative_units"] == 1
    assert report["rows_reusing_shared_source_narratives"] == 2
    assert report["exact_duplicate_text_groups"] == 1


def test_partial_unresolved_transclusion_retains_meaningful_local_text():
    pages = {
        "Comic 1": page(
            "Comic 1", {"Synopsis1": "Batman arrives in Gotham. {{StoryGrab|Uncached Comic|1}}"}
        )
    }
    table, report = build([issue()], pages)
    assert table.iloc[0].synopsis_text == "Batman arrives in Gotham."
    assert table.iloc[0].text_status == "partial_or_multiple_cached_transclusion"
    assert report["stories_with_any_available_synopsis"] == 1
    assert report["stories_all_selected_synopses_available_and_reading_list_complete"] == 0
