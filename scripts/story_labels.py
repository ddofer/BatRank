"""Export explicit issue labels from the cached wiki snapshot; no network requests."""

import re

import mwparserfromhell
import pandas as pd

from scripts.dataset import Fetcher, ROOT, clean, wiki_pages
from scripts.enrich import fields_for


def issue_labels(page):
    """Missing labels are unrecorded, not evidence that a label does not apply."""
    revisions = (page or {}).get("revisions", [])
    if not revisions:
        return None
    text = revisions[0]["slots"]["main"]["*"]
    code = mwparserfromhell.parse(text)
    categories = {
        str(link.title).strip().casefold()
        for link in code.filter_wikilinks()
        if str(link.title).strip().casefold().startswith("category:")
    }
    templates = {str(t.name).strip().casefold() for t in code.filter_templates()}
    fields = fields_for(page)
    events = sorted(
        {
            clean(value)
            for key, value in fields.items()
            if re.fullmatch(r"Event\d*", key) and clean(value)
        }
    )
    return {
        "elseworlds": "elseworlds" in templates or "category:elseworlds" in categories,
        "graphic_novel": "category:graphic novels" in categories,
        "events": events,
    }


def main():
    stories = pd.read_csv(ROOT / "data/processed/stories.csv")
    issues = pd.read_csv(ROOT / "data/processed/issues.csv")
    assert stories.story_id.is_unique
    assert not issues.duplicated(["story_id", "requested_title"]).any()
    assert set(issues.story_id) <= set(stories.story_id)
    pages = wiki_pages(Fetcher(offline=True), issues.lookup_title.dropna().unique().tolist())
    parsed = {title: issue_labels(page) for title, page in pages.items()}
    rows = []
    for story_id, refs in issues.groupby("story_id", sort=False):
        labels = [parsed.get(row.lookup_title) for row in refs.itertuples()]
        available = [label for label in labels if label is not None]
        row = {
            "story_id": story_id,
            "reference_count": len(refs),
            "labelled_issue_count": len(available),
            "label_issue_coverage": len(available) / len(refs),
        }
        for name in ["elseworlds", "graphic_novel", "event"]:
            key = "events" if name == "event" else name
            hits = [bool(label and label[key]) for label in labels]
            row[f"{name}_issue_count"] = sum(hits)
            row[f"{name}_source_urls"] = "|".join(
                sorted(set(refs.loc[hits, "metadata_url"].dropna()))
            )
        row["event_names"] = "|".join(
            sorted({event for label in available for event in label["events"]})
        )
        rows.append(row)
    result = stories[["story_id"]].merge(
        pd.DataFrame(rows), on="story_id", how="left", validate="one_to_one"
    )
    assert len(result) == len(stories)
    assert result.label_issue_coverage.dropna().between(0, 1).all()
    for name in ["elseworlds", "graphic_novel", "event"]:
        known = result.labelled_issue_count.notna()
        assert (
            result.loc[known, f"{name}_issue_count"]
            .le(result.loc[known, "labelled_issue_count"])
            .all()
        )
    result.to_csv(ROOT / "data/external/story_labels.csv", index=False)


if __name__ == "__main__":
    main()
