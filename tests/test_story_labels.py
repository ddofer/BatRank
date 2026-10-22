from scripts.story_labels import issue_labels


def test_explicit_labels_ignore_plot_mentions():
    def page(text):
        return {"revisions": [{"slots": {"main": {"*": text}}}]}

    found = issue_labels(
        page("""{{DC Database:Comic Template
| Event = [[Batman: Knightfall]]
| Event2 = Batman: Knightfall
| Synopsis1 = An Elseworlds crossover with a graphic novel.
}}{{Elseworlds}} [[Category:Graphic Novels]]""")
    )
    assert found == {"elseworlds": True, "graphic_novel": True, "events": ["Batman: Knightfall"]}
    assert issue_labels(page("{{DC Database:Comic Template|Synopsis1=Elseworlds}}")) == {
        "elseworlds": False,
        "graphic_novel": False,
        "events": [],
    }
    assert issue_labels({}) is None
