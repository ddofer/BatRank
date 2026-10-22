"""Check notebook series grouping and rendered table sizes."""

import json
from pathlib import Path

import pandas as pd


def test_series_combines_volumes_and_counts_each_story_once():
    notebook = json.loads(
        (Path(__file__).parents[1] / "notebooks/2.2-batchat-plot-words.ipynb").read_text()
    )
    source = next(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if "series_links = issues" in "".join(cell["source"])
    ).split("series_rankings =")[0]
    namespace = {
        "issues": pd.DataFrame(
            {
                "story_id": ["a", "a", "b", "c"],
                "wiki_title": [
                    "Batman Adventures Vol 1 9",
                    "Batman Adventures Vol 2 9",
                    "Batman Adventures Vol 2 10",
                    "Batman Vol 2 23.1",
                ],
            }
        ),
        "stories": pd.DataFrame(
            {"story_id": ["a", "b", "c"], "rank": [1, 2, 3], "title": ["A", "B", "C"]}
        ),
    }
    exec(source, namespace)
    result = namespace["series_links"]
    assert list(zip(result.story_id, result.Series)) == [
        ("a", "Batman Adventures"),
        ("b", "Batman Adventures"),
        ("c", "Batman"),
    ]


def test_rendered_notebook_tables_have_fewer_than_25_rows():
    from html.parser import HTMLParser

    class TableRows(HTMLParser):
        def __init__(self):
            super().__init__()
            self.in_body = False
            self.rows = 0
            self.counts = []

        def handle_starttag(self, tag, attrs):
            if tag == "tbody":
                self.in_body = True
            elif tag == "tr" and self.in_body:
                self.rows += 1

        def handle_endtag(self, tag):
            if tag == "tbody":
                self.in_body = False
            elif tag == "table":
                self.counts.append(self.rows)
                self.rows = 0

    for path in (Path(__file__).parents[1] / "notebooks").glob("*.ipynb"):
        parser = TableRows()
        for cell in json.loads(path.read_text())["cells"]:
            for output in cell.get("outputs", []):
                parser.feed("".join(output.get("data", {}).get("text/html", [])))
        assert parser.counts, path.name
        assert all(rows < 25 for rows in parser.counts), (path.name, parser.counts)
