"""Parse the deliberately small, verified GCD sample from indexed primary records.

Direct GCD requests were challenged; these snapshots came from ordinary web search.
No bot challenge, authentication requirement, or private API is circumvented.
Run: python -m scripts.catalogue
"""

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/catalogue"
LICENSE = "https://creativecommons.org/licenses/by-sa/4.0/"


def parse_records(text):
    """Read visible issue/story fields, excluding search snippets and cover sequences."""
    records = []
    for block in text.split(
        "--------------------------------------------------------------------------------"
    ):
        header = re.search(
            r"^GCD :: Issue :: (.*?) \((https://(?:www|my)\.comics\.org/issue/(\d+)/[^\s]*)\)\s*$",
            block,
            re.M,
        )
        if not header:
            continue
        body = "\n".join(line for line in block.splitlines()[1:] if "[wordlim:" not in line)
        sections = list(
            re.finditer(
                r"(?m)^([^\n#][^\n]*)\n+\((?:Expand\) / \()?Table of Contents(?:: (\d+))?\)", body
            )
        )
        physical = re.search(r"(?m)^Pages:\s*(\d+(?:\.\d+)?)\s*$", body)
        sale = re.search(r"(?m)^On-sale Date:\s*(\d{4}-\d{2}-\d{2})\s*$", body)
        isbn = re.search(r"(?m)^\s*\* ISBN:\s*([^\n]+)", body)
        for i, section in enumerate(sections):
            content = body[
                section.end() : sections[i + 1].start() if i + 1 < len(sections) else len(body)
            ]
            narrative = re.search(
                r"(?m)^(?:[^\n]* / )?(comic story|text story) / (\d+(?:\.\d+)?) pages?\s*$", content
            )
            if (
                not narrative
                or not re.fullmatch(r"[\s#]*", content[: narrative.start()])
                or section[1].startswith(("*", "GCD ::", "http"))
            ):
                continue
            credits = dict(
                re.findall(
                    r"(?m)^(Script|Pencils|Inks|Colors|Letters|Editing):\s*\|\s*([^\n]+)", content
                )
            )
            # A clipped indexed record can omit credits; missing stays missing.
            records.append(
                {
                    "catalogue_url": header[2],
                    "catalogue_issue_id": int(header[3]),
                    "catalogue_issue_label": header[1],
                    "catalogue_sequence": int(section[2] or 0),
                    "narrative_title": section[1].strip(),
                    "narrative_type": narrative[1],
                    "narrative_page_count": float(narrative[2]),
                    "physical_issue_page_count": float(physical[1]) if physical else None,
                    "on_sale_date": sale[1] if sale else None,
                    "isbn": isbn[1].strip() if isbn else None,
                    "credit_strings": credits,
                    "reprint_labels": re.findall(r"(?m)^\s*\* Image: [^\n]+? in ([^\n]+)", content),
                }
            )
    unique = {}
    for record in records:
        key = record["catalogue_issue_id"], record["catalogue_sequence"], record["narrative_title"]
        score = (
            len(record["credit_strings"])
            + bool(record["physical_issue_page_count"])
            + bool(record["on_sale_date"])
        )
        previous = unique.get(key)
        if previous is None or score > previous[0]:
            unique[key] = score, record
    return [record for _, record in unique.values()]


def build():
    selections = json.loads((RAW / "matches.json").read_text())
    records = []
    parsed = {}
    for match in selections:
        filename = match["snapshot_file"]
        if filename not in parsed:
            parsed[filename] = parse_records((RAW / filename).read_text())
        candidates = [
            r
            for r in parsed[filename]
            if r["catalogue_issue_id"] == match["catalogue_issue_id"]
            and r["catalogue_sequence"] == match["catalogue_sequence"]
            and r["narrative_title"] == match["narrative_title"]
        ]
        if len(candidates) != 1:
            raise ValueError(
                f"Expected one exact indexed narrative: {match}; got {len(candidates)}"
            )
        if match["expected_issue"] not in candidates[0]["catalogue_issue_label"]:
            raise ValueError(f"Issue identity mismatch: {match}")
        record = {**candidates[0], **match, "acquisition_mode": "indexed_primary_record"}
        if record["match_scope"] == "same_story_reprint":
            record["on_sale_date"] = None
            record["physical_issue_page_count"] = None
        assert 0 < record["narrative_page_count"] < 1000
        records.append(record)
    keys = [(r["story_id"], r["wiki_title"], r["narrative_title"]) for r in records]
    assert len(keys) == len(set(keys)), "Duplicate narrative associations"
    stories, issues = aggregates(records)
    publisher_records = []
    publisher_matches = RAW / "publisher_matches.json"
    if publisher_matches.exists():
        by_story = {row["story_id"]: row for row in stories}
        for match in json.loads(publisher_matches.read_text()):
            publisher = parse_publisher((RAW / match["snapshot_file"]).read_text())
            if publisher["publisher_edition_title"] != match["expected_title"]:
                raise ValueError(f"Wrong publisher edition: {match}")
            publisher = {**publisher, **match, "acquisition_mode": "public_primary_record"}
            publisher_records.append(publisher)
            row = by_story.setdefault(match["story_id"], {"story_id": match["story_id"]})
            row.update(
                {key: value for key, value in publisher.items() if key.startswith("publisher_")}
            )
        stories = list(by_story.values())
    output = {
        "source": "Grand Comics Database",
        "license": "CC BY-SA 4.0",
        "license_scope": "GCD-derived records and fields only; publisher_sources documents DC's separate rights.",
        "license_url": LICENSE,
        "retrieved_date": "2026-10-21",
        "acquisition_mode": "indexed_primary_record",
        "sample_design": "Purposive: high/low ranks, silent comic, illustrated prose, backup stories, and issue/collection scope checks. Not representative.",
        "limitations": [
            "Direct requests received Cloudflare 403; only indexed primary text was used.",
            "Indexed text can be clipped or stale; missing fields are not negative observations.",
            "Fractional narrative pages are retained as recorded by GCD.",
            "Reprints can change story length or coloring; reprint matches are explicitly marked.",
            "Credit strings retain GCD's attribution qualifiers; adjacent creator names are not guessed apart.",
        ],
        "records": records,
        "stories": stories,
        "issues": issues,
        "publisher_records": publisher_records,
        "publisher_sources": {
            "source": "DC official catalogue",
            "license": "No blanket open-data license asserted",
            "rights_note": "Only product facts and credited names exported; no descriptions or cover images copied into the dataset.",
        },
    }
    destination = ROOT / "data/external/catalogue.json"
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    pd.DataFrame(records)[
        [
            "story_id",
            "wiki_title",
            "narrative_title",
            "narrative_type",
            "narrative_page_count",
            "match_scope",
            "catalogue_url",
            "catalogue_issue_id",
            "catalogue_sequence",
        ]
    ].to_csv(ROOT / "references/catalogue_narratives.csv", index=False)
    print(f"{len(records)} narrative units; {len({r['story_id'] for r in records})} ranked stories")
    return output


def parse_publisher(text):
    """Read DC's visible product specs; edition pages are never narrative pages."""
    source = re.search(r"\((https://www\.dc\.com/[^\s]+)\)", text)
    body = re.sub(r"L\d+: ?", "\n", text)
    body = re.sub(r"cite\d+†([^†]+)(?:†[^]+)?", r"\1", body)
    title = re.search(r"(?m)^# (.+)$", body)
    pages = re.search(r"Page Count:\s*\n+\s*(\d+)", body)
    sale = re.search(r"On Sale Date:\s*\n+\s*([^\n]+)", body)
    if not all([source, title, pages, sale]):
        raise ValueError("Missing publisher identity or specs")
    date = re.sub(r"(?<=\d)(?:st|nd|rd|th)", "", sale[1])
    result = {
        "publisher_source_url": source[1],
        "publisher_edition_title": title[1],
        "publisher_physical_page_count": int(pages[1]),
        "publisher_edition_on_sale_date": datetime.strptime(date, "%A, %B %d, %Y")
        .date()
        .isoformat(),
    }
    talent = body.split("### Talent", 1)[1].split("### SPECS", 1)[0]
    sections = re.split(r"(?m)^(Written by|Art by|Colorist|Letterer|Cover by):\s*$", talent)
    roles = {
        "Written by": "writers",
        "Art by": "artists",
        "Colorist": "colorists",
        "Letterer": "letterers",
        "Cover by": "cover_artists",
    }
    for label, content in zip(sections[1::2], sections[2::2]):
        names = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and line.strip() != "Various"
        ]
        result["publisher_" + roles[label]] = "; ".join(dict.fromkeys(names))
    return result


def aggregates(records):
    """Only complete original-issue coverage receives a full ranked-story page count."""
    canonical = pd.read_csv(ROOT / "data/processed/stories.csv").set_index("story_id")
    references = pd.read_csv(ROOT / "data/processed/issues.csv")
    stories, issues = [], []
    for story_id in sorted({r["story_id"] for r in records}):
        sample = [r for r in records if r["story_id"] == story_id]
        original = [r for r in sample if r["match_scope"] == "original_issue"]
        reading_list = references.loc[references.story_id.eq(story_id)]
        sampled_titles = {r["wiki_title"] for r in sample}
        original_titles = {r["wiki_title"] for r in original}
        assert sampled_titles <= set(reading_list.wiki_title.dropna()), "Unknown canonical issue"
        assert canonical.loc[story_id, "issue_list_complete"] in [True, False]
        complete = bool(canonical.loc[story_id, "issue_list_complete"]) and len(
            original_titles
        ) == len(reading_list)
        stories.append(
            {
                "story_id": story_id,
                "gcd_narrative_page_count": round(
                    sum(r["narrative_page_count"] for r in original), 2
                )
                if complete
                else None,
                "gcd_sampled_narrative_page_count": round(
                    sum(r["narrative_page_count"] for r in sample), 2
                ),
                "gcd_sampled_reference_count": len(sampled_titles),
                "gcd_matched_reference_count": len(original_titles),
                "gcd_reference_coverage": len(original_titles) / len(reading_list),
                "gcd_page_count_scope": "complete_ranked_narratives"
                if complete
                else "partial_or_reprint_sample",
                "gcd_story_types": "; ".join(sorted({r["narrative_type"] for r in sample})),
                "gcd_source_urls": "; ".join(sorted({r["catalogue_url"] for r in sample})),
            }
        )
        for wiki_title in sorted(sampled_titles):
            selected = [r for r in sample if r["wiki_title"] == wiki_title]
            matches = reading_list.loc[reading_list.wiki_title.eq(wiki_title)]
            assert len(matches) == 1, "Ambiguous canonical association"
            exact = all(r["match_scope"] == "original_issue" for r in selected)
            issues.append(
                {
                    "story_id": story_id,
                    "requested_title": matches.requested_title.iloc[0],
                    "gcd_narrative_page_count": round(
                        sum(r["narrative_page_count"] for r in selected), 2
                    )
                    if exact
                    else None,
                    "gcd_narrative_titles": "; ".join(r["narrative_title"] for r in selected),
                    "gcd_story_types": "; ".join(sorted({r["narrative_type"] for r in selected})),
                    "gcd_physical_issue_page_count": selected[0]["physical_issue_page_count"]
                    if exact
                    else None,
                    "gcd_on_sale_date": selected[0]["on_sale_date"] if exact else None,
                    "gcd_source_urls": "; ".join(sorted({r["catalogue_url"] for r in selected})),
                    "gcd_match_scope": "original_issue" if exact else "same_story_reprint",
                }
            )
    return stories, issues


if __name__ == "__main__":
    build()
