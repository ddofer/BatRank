"""Check the notebook's series grouping against relaunch and duplicate references."""

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
