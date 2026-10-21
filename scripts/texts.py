"""Export full available wiki synopses for the selected indexed narratives, cache only.

These are fan-written plot descriptions, not comic dialogue or the original prose.
One row identifies a ranked reading's issue/substory; no ordering or arc concatenation
is imposed. Text availability does not establish that a synopsis covers the whole plot.
"""

import argparse
import hashlib
import json
import re
from urllib.parse import quote

import mwparserfromhell
import pandas as pd

from scripts.dataset import Fetcher, ROOT, wiki_pages
from scripts.enrich import clean, fields_for, substory_indexes

SOURCE_LICENSE = "CC-BY-SA; applicable terms: https://www.fandom.com/licensing"
COLUMNS = [
    "story_id",
    "requested_title",
    "wiki_title",
    "issue_id",
    "substory_index",
    "substory_title",
    "synopsis_text",
    "synopsis_word_count",
    "text_status",
    "source_substory_index",
    "source_url",
    "revision_id",
    "revision_timestamp",
    "revision_url",
    "source_license",
]
STUB = re.compile(
    r"(?:the )?(?:synopsis|summary|plot(?: summary)?)(?: for (?:this|the) (?:issue|story|comic))? "
    r"(?:has not (?:yet )?been written|has not been written yet|is (?:not (?:yet )?(?:written|available)|missing)|"
    r"(?:is )?(?:needed|coming soon|to (?:be )?(?:added|written)))"
    r"|(?:no (?:synopsis|summary)(?: (?:is )?(?:available|yet))?)"
    r"|(?:to be (?:added|written)|coming soon|under construction|tba|tbd|n/?a|unknown)",
    re.I,
)


def plain_synopsis(value):
    """Remove markup/citations/instructions, retaining all remaining prose and paragraphs."""
    # A few synopsis fields contain review sections or anthology credit headers.
    value = value.replace(
        "Five [[Batman]] stories by some of comics' top creators. Each story is accompanied "
        "with a one-page profile of the artist or artists who worked on it.",
        "",
    )
    value = re.sub(r"(?m)^'''(?:Writer|Artist):'''[^\n]*(?:\n|$)", "", value)
    value = re.sub(r"(?m)^'''Synopsis:'''(?:<br\s*/?>)?[ \t]*(?:\n|$)", "", value)
    code = mwparserfromhell.parse(value)
    kept, omitted_level = [], None
    for node in code.nodes:
        if isinstance(node, mwparserfromhell.nodes.Heading):
            if omitted_level is not None and node.level <= omitted_level:
                omitted_level = None
            if omitted_level is None and str(node.title).strip().casefold() in {
                "reception",
                "critical reception",
            }:
                omitted_level = node.level
        if omitted_level is None:
            kept.append(node)
    code = mwparserfromhell.wikicode.Wikicode(kept)
    for tag in reversed(code.filter_tags()):
        if str(tag.tag).strip().casefold() in {"ref", "references", "gallery", "imagemap"}:
            code.remove(tag)
    for tag in reversed(code.filter_tags()):
        name = str(tag.tag).strip().casefold()
        if name == "br":
            code.replace(tag, "\n")
        elif name in {"p", "div", "li"}:
            code.replace(tag, "\n\n" + str(tag.contents or "") + "\n\n")
    # Render only simple link/display templates; unknown/stub templates are not prose.
    for template in list(code.filter_templates(recursive=False)):
        name = str(template.name).strip().casefold()
        if name in {"a", "wp", "w", "c", "co", "nowrap", "small"} and template.has(1):
            param = 2 if name in {"wp", "w", "c", "co"} and template.has(2) else 1
            code.replace(template, str(template.get(param).value))
        elif name == "pullquote" and template.has(2):
            code.replace(template, str(template.get(2).value))
        elif name in {"quote", "blockquote", "quotewithcat"} and template.has(1):
            code.replace(template, str(template.get(1).value))
        else:
            code.remove(template)
    for link in list(code.filter_wikilinks()):
        if str(link.title).strip().casefold().startswith(("file:", "image:", "category:")):
            code.remove(link)
    text = code.strip_code(normalize=True, collapse=True)
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text):
        lines = []
        for line in paragraph.splitlines():
            line = re.sub(r"[ \t\r\f\v]+", " ", line).strip()
            instruction = line.strip(" .:;!?*#'\"[]()")
            if (
                not line
                or STUB.fullmatch(instruction)
                or re.fullmatch(
                    r"(?:synopsis|summary)(?: (?:is )?not (?:yet )?written| (?:needed|coming soon|tba|tbd))",
                    instruction,
                    re.I,
                )
            ):
                continue
            if re.fullmatch(
                r"(?:this (?:article|page|issue|story) (?:is missing|needs|requires).*(?:synopsis|summary).*|please (?:add|write|provide).*(?:synopsis|summary).*)",
                instruction,
                re.I,
            ):
                continue
            lines.append(line)
        if lines:
            paragraphs.append(" ".join(lines))
    return "\n\n".join(paragraphs).strip() or None


def selected_indexes(value):
    if pd.isna(value) or not str(value).strip():
        return []
    tokens = str(value).split("|")
    if not all(re.fullmatch(r"\d+(?:\.0)?", token.strip()) for token in tokens):
        raise ValueError(f"Invalid selected substory indexes: {value!r}")
    return sorted({int(float(token)) for token in tokens})


def synopsis_source(page, index, pages, parsed, seen=None):
    """Follow explicit cached StoryGrab references, never a guessed first story."""
    seen = set() if seen is None else seen
    key = (page.get("title"), index)
    if key in seen:
        return None, page, index, "cyclic_cached_transclusion"
    seen.add(key)
    fields = parsed.get(page.get("title"), {})
    if index not in substory_indexes(fields):
        return None, page, index, "stale_selected_substory_index"
    value = fields.get(f"Synopsis{index}", "")
    code = mwparserfromhell.parse(value)
    grabs = [
        t
        for t in code.filter_templates(recursive=False)
        if str(t.name).strip().casefold() == "storygrab"
    ]
    if grabs:
        residual = mwparserfromhell.parse(value)
        for template in list(residual.filter_templates(recursive=False)):
            if str(template.name).strip().casefold() == "storygrab":
                residual.remove(template)
        if len(grabs) != 1 or plain_synopsis(str(residual)):
            return (
                plain_synopsis(str(residual)),
                page,
                index,
                "partial_or_multiple_cached_transclusion",
            )
        template = grabs[0]
        if not template.has(1) or not template.has(2):
            return None, page, index, "invalid_cached_transclusion"
        title = str(template.get(1).value).strip().replace("_", " ")
        number = str(template.get(2).value).strip()
        if title not in pages or not re.fullmatch(r"\d+", number):
            return None, page, index, "missing_cached_transclusion"
        return synopsis_source(pages[title], int(number), pages, parsed, seen)
    text = plain_synopsis(value)
    return text, page, index, "available" if text else "missing_synopsis"


def build_texts(stories, issues, pages):
    if "selected_substory_indexes" not in issues:
        raise ValueError("Run narrative enrichment before extracting synopsis texts")
    if not stories.story_id.is_unique or issues.duplicated(["story_id", "requested_title"]).any():
        raise ValueError("Duplicate canonical story/reference keys")
    if not set(issues.story_id) <= set(stories.story_id):
        raise ValueError("Issue reference has an unknown story ID")
    # Multiple lookup aliases can refer to one canonical cached page.
    canonical_pages = {page.get("title"): page for page in pages.values()}
    parsed = {
        title: fields_for(page)
        for title, page in canonical_pages.items()
        if "Comic Template"
        in page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
    }
    all_pages = {**canonical_pages, **pages}
    records, transcluded = [], 0
    for issue in issues.itertuples():
        page = pages.get(issue.lookup_title, {})
        indexes = selected_indexes(issue.selected_substory_indexes)
        for index in indexes or [None]:
            text, source, source_index, status = (
                synopsis_source(page, index, all_pages, parsed)
                if index is not None
                else (None, page, None, "unresolved_substory_selection")
            )
            revision = source.get("revisions", [{}])[0]
            url = source.get("fullurl") or source.get("canonicalurl")
            if not url and pd.notna(issue.wiki_title):
                url = "https://dc.fandom.com/wiki/" + quote(str(issue.wiki_title).replace(" ", "_"))
            revision_id = revision.get("revid")
            transcluded += int(status == "available" and source.get("title") != page.get("title"))
            records.append(
                {
                    "story_id": issue.story_id,
                    "requested_title": issue.requested_title,
                    "wiki_title": issue.wiki_title if pd.notna(issue.wiki_title) else None,
                    "issue_id": issue.issue_id if pd.notna(issue.issue_id) else None,
                    "substory_index": index,
                    "substory_title": clean(
                        parsed.get(page.get("title"), {}).get(f"StoryTitle{index}", "")
                    )
                    or None
                    if index is not None
                    else None,
                    "synopsis_text": text,
                    "synopsis_word_count": len(text.split()) if text else 0,
                    "text_status": status,
                    "source_url": url,
                    "revision_id": revision_id,
                    "revision_timestamp": revision.get("timestamp"),
                    "revision_url": f"{url}?oldid={revision_id}"
                    if url and revision_id is not None
                    else None,
                    "source_license": SOURCE_LICENSE,
                    "source_substory_index": source_index,
                }
            )
    table = pd.DataFrame(records)
    for column in ["issue_id", "substory_index", "source_substory_index", "revision_id"]:
        table[column] = pd.array(table[column], dtype="Int64")
    assert not table.duplicated(["story_id", "requested_title", "substory_index"]).any()
    available = table.loc[table.text_status.eq("available")]
    has_text = set(table.loc[table.synopsis_text.notna(), "story_id"])
    all_rows_available = table.groupby("story_id").text_status.agg(
        lambda values: values.eq("available").all()
    )
    complete_lists = set(stories.loc[stories.issue_list_complete.eq(True), "story_id"])
    complete = set(all_rows_available.index[all_rows_available]) & complete_lists
    duplicated = available.groupby(
        ["source_url", "revision_id", "source_substory_index"], dropna=False
    ).size()
    text_hashes = available.synopsis_text.map(
        lambda text: hashlib.sha256(text.encode()).hexdigest()
    ).value_counts()
    report = {
        "stories": len(stories),
        "exported_rows": len(table),
        "selected_substory_rows": int(table.substory_index.notna().sum()),
        "available_synopsis_rows": len(available),
        "rows_with_any_clean_text": int(table.synopsis_text.notna().sum()),
        "stories_with_any_available_synopsis": len(has_text),
        "stories_all_selected_synopses_available_and_reading_list_complete": len(complete),
        "stories_with_unresolved_substory_selection": int(
            table.loc[table.text_status.eq("unresolved_substory_selection"), "story_id"].nunique()
        ),
        "selected_rows_missing_clean_text": int(
            (table.substory_index.notna() & table.text_status.ne("available")).sum()
        ),
        "text_status_counts": {
            key: int(value) for key, value in table.text_status.value_counts().items()
        },
        "total_exported_words": int(available.synopsis_word_count.sum()),
        "longest_synopsis_characters": int(available.synopsis_text.str.len().max())
        if len(available)
        else 0,
        "cached_transclusion_rows": transcluded,
        "shared_source_narrative_units": int(duplicated.gt(1).sum()),
        "rows_reusing_shared_source_narratives": int(duplicated.loc[duplicated.gt(1)].sum()),
        "exact_duplicate_text_groups": int(text_hashes.gt(1).sum()),
        "scope_note": "One row per selected indexed narrative, including missing synopses; one unresolved-selection row per unresolved reference. Available means non-placeholder cleaned source text exists, not that the synopsis is a complete plot description. Plot length is uncapped. Explicit reception sections and anthology credit headers are removed. These are wiki contributors' descriptions, not the comic's dialogue, captions or original prose.",
        "provenance_note": "Explicit StoryGrab transclusions use only already cached target/index pairs. Source URL/revision identify the actual synopsis source; wiki_title/issue_id identify the ranked reference. No ordering or whole-arc text is constructed.",
        "validation_note": "Shared source narratives and exact duplicate synopses can occur in multiple ranked readings. Keep overlapping texts together when validating future NLP models.",
        "source_license": SOURCE_LICENSE,
    }
    return table[COLUMNS], report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline", action="store_true", help="Always cache-only; accepted for consistency"
    )
    parser.parse_args()
    stories = pd.read_csv(ROOT / "data/processed/stories.csv")
    issues = pd.read_csv(ROOT / "data/processed/issues.csv")
    pages = wiki_pages(Fetcher(offline=True), issues.lookup_title.dropna().unique().tolist())
    cache = ROOT / "data/interim/wiki_pages.json"
    if cache.exists():
        pages = {**json.loads(cache.read_text()), **pages}
    table, report = build_texts(stories, issues, pages)
    table.to_csv(ROOT / "data/processed/story_texts.csv", index=False)
    (ROOT / "reports/texts_validation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in report.items() if not key.endswith("note")}, indent=2
        )
    )


if __name__ == "__main__":
    main()
