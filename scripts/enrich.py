"""Extract narrative, cast and collection features from the existing DC Wiki snapshot.

Run ``python -m scripts.enrich --offline`` before rebuilding the canonical tables.
No network calls are made. Linked wiki page titles are identifiers, not resolved redirects.
"""

import argparse
import collections
import json
import re
import unicodedata
from urllib.parse import quote

import mwparserfromhell
import pandas as pd

from scripts.dataset import Fetcher, ROOT, ROLES, clean, wiki_pages

NARRATIVE_ROLES = {
    k: v for k, v in ROLES.items() if k not in {"cover_artists", "executive_editors"}
}
SECTIONS = {
    "featured characters": "featured",
    "supporting characters": "supporting",
    "antagonists": "antagonists",
    "villains": "antagonists",
    "other characters": "other",
    "others": "other",
    "mentioned characters": "other",
    "supporting character": "supporting",
    "location": "locations",
    "locations": "locations",
}
MODES = ("mentioned", "flashback", "cameo", "depiction", "behind_scenes", "ordinary")


def normalize_title(value):
    text = unicodedata.normalize("NFKD", clean(value)).casefold()
    text = re.sub(r"\b(?:part|chapter|book)\s+(?:\d+|[ivxlcdm]+)\b", "", text)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def fields_for(page):
    if not page or "revisions" not in page:
        return {}
    code = mwparserfromhell.parse(page["revisions"][0]["slots"]["main"]["*"])
    template = next((t for t in code.filter_templates() if "Comic Template" in str(t.name)), None)
    return {str(p.name).strip(): str(p.value).strip() for p in template.params} if template else {}


def substory_indexes(fields):
    indexes = set()
    for key, value in fields.items():
        if not value.strip():
            continue
        match = re.fullmatch(
            r"(?:StoryTitle|Appearing|Synopsis)(\d+)|(?:Writer|Penciler|Inker|Colorist|Letterer|Editor)(\d+)_\d+",
            key,
        )
        if match:
            indexes.add(int(match[1] or match[2]))
    return sorted(indexes)


def select_substories(title, fields, override=None):
    """Resolve only a single indexed story, explicitly named stories or a reviewed override."""
    indexes = substory_indexes(fields)
    if override is not None:
        selected = (
            [
                i
                for i in indexes
                if not re.search(
                    r"^(?:pinups?|letters|exclusive behind.the.scenes|.*(?:cover comparison|character design|pencils to inks comparison|script to art comparison)|batman gallery)$",
                    normalize_title(fields.get(f"StoryTitle{i}", "")),
                )
            ]
            if override == "all"
            else list(override)
        )
        if not set(selected) <= set(indexes):
            raise ValueError(
                f"Override refers to absent substories: {title}: {selected} / {indexes}"
            )
        return selected, "reviewed_override"
    if len(indexes) == 1:
        return indexes, "single_substory"
    if not indexes:
        return [], "no_indexed_substories"
    target = normalize_title(title)
    selected = []
    for index in indexes:
        candidate = normalize_title(fields.get(f"StoryTitle{index}", ""))
        if candidate and candidate == target and target not in {"batman", "superman", "robin"}:
            selected.append(index)
        elif (
            len(candidate.split()) >= 2
            and len(candidate) >= 10
            and f" {candidate} " in f" {target} "
        ):
            selected.append(index)
        elif len(target.split()) >= 2 and len(target) >= 10 and f" {target} " in f" {candidate} ":
            selected.append(index)
    return (selected, "explicit_title_match") if selected else ([], "ambiguous_whole_issue")


def linked_entities(value):
    """Retain wiki targets, including universe qualifiers; do not merge namesakes."""
    entities = {}
    for link in mwparserfromhell.parse(value).filter_wikilinks():
        target = str(link.title).strip().replace("_", " ").split("#", 1)[0]
        if not target or ":" in target.split("(", 1)[0] or "|" in target or "{" in target:
            continue
        entities[target] = clean(link.text if link.text is not None else target)
    return entities


def appearance_line_parts(line):
    """Separate leading appearance links from notes and their explanatory links."""
    code = mwparserfromhell.parse(re.sub(r"^\s*\*+\s*", "", line))
    entities = {}
    annotations = []
    in_annotations = False
    for node in code.nodes:
        if isinstance(node, mwparserfromhell.nodes.Template):
            if str(node.name).strip().casefold() == "a" and not in_annotations and node.has(1):
                entities.update(linked_entities(str(node.get(1).value)))
            else:
                in_annotations = True
                annotations.append(str(node.name))
                annotations.extend(clean(p.value) for p in node.params)
        elif isinstance(node, mwparserfromhell.nodes.Wikilink) and not in_annotations:
            entities.update(linked_entities(str(node)))
        else:
            text = str(node).strip()
            if text and not re.fullmatch(r"(?:[,/;&]|and|or|['\s])+", text):
                in_annotations = True
                annotations.append(clean(text))
                # A link decorating an unnamed waiter is not an appearance of the hero.
                if re.match(r"-themed\b", text, re.I):
                    entities.clear()
    return entities, " ".join(annotations).casefold()


def appearance_entities(value):
    """Parse role headings and per-line appearance qualifiers, never synopsis mentions."""
    rows = []
    section = None
    parent_modes = {}
    heading_mode = None
    for line in value.splitlines():
        heading = re.match(r"^\s*'''\s*([^':\n]+):?\s*'''\s*:?(?:\s|$)", line)
        if heading:
            label = heading[1].strip().casefold()
            section = SECTIONS.get(label)
            heading_mode = "mentioned" if label == "mentioned characters" else None
            parent_modes = {}
            continue
        bullet = re.match(r"\s*(\*+)", line)
        if not bullet or section is None:
            continue
        depth = len(bullet[1])
        parent_modes = {d: modes for d, modes in parent_modes.items() if d < depth}
        entities, qualifiers = appearance_line_parts(line)
        flash_both = "flashalso" in qualifiers or bool(
            re.search(
                r"flashback.*(?:main story|present)|(?:main story|present).*flashback", qualifiers
            )
        )
        mode = (
            "mentioned"
            if re.search(r"mention", qualifiers)
            else "flashback"
            if re.search(r"flashback", qualifiers) and not flash_both
            else "cameo"
            if re.search(r"cameo", qualifiers)
            else "depiction"
            if re.search(
                r"(?:photo|picture|illusion|dream|vision(?!also)|hallucination|hologram|video|image|corpse|\btv\b)",
                qualifiers,
            )
            else "behind_scenes"
            if re.search(r"\bbts\b|behind the scenes", qualifiers)
            else "ordinary"
        )
        modes = [mode]
        if mode == "ordinary":
            modes = parent_modes.get(depth - 1, [heading_mode or mode]).copy()
            if flash_both:
                modes.append("flashback")
            if "visionalso" in qualifiers:
                modes.append("depiction")
        parent_modes[depth] = list(dict.fromkeys(modes))
        for target, display in entities.items():
            for mode in dict.fromkeys(modes):
                rows.append({"id": target, "name": display, "role": section, "mode": mode})
    return rows


def collection_targets(fields, selected=None, substory_count=None):
    """Notes are evidence of issue-associated reprints, not a complete edition bibliography."""
    notes = fields.get("Notes", "")
    links = set()
    for template in mwparserfromhell.parse(notes).filter_templates():
        if str(template.name).strip().casefold() == "co" and template.has(1):
            target = clean(template.get(1).value)
            if target:
                links.add(target)
    for target in linked_entities(notes):
        if "(Collected)" in target:
            links.add(target)
    return sorted(links)


def indexed_credits(fields, selected, indexes):
    result = {}
    for role, prefix in NARRATIVE_ROLES.items():
        names = set()
        for key, value in fields.items():
            match = re.fullmatch(re.escape(prefix) + r"(\d+)(?:_(\d+))?", key)
            if not match:
                continue
            # Modern indexed fields are Role<story>_<person>; older Role1/Role2 mean
            # contributor numbers and can only be assigned when one story is indexed.
            belongs = (
                int(match[1]) in selected if match[2] else len(indexes) == 1 and bool(selected)
            )
            if belongs and clean(value).casefold() not in {
                "",
                "n/a",
                "unknown",
                "uncredited",
                "none",
                "?",
            }:
                names.add(clean(value))
        result[f"narrative_{role}"] = "|".join(sorted(names)) or None
    return result


def enrich_issue(story, issue, fields, override=None):
    indexes = substory_indexes(fields)
    selected, status = select_substories(story.title, fields, override)
    appearance_indexes = selected or indexes
    indexed_appearances = {
        i: appearance_entities(fields.get(f"Appearing{i}", "")) for i in appearance_indexes
    }
    entities = [r for rows in indexed_appearances.values() for r in rows]
    result = {
        "story_id": story.story_id,
        "requested_title": issue.requested_title,
        "indexed_substory_count": len(indexes),
        "selected_substory_indexes": "|".join(map(str, selected)) or None,
        "selected_substory_titles": "|".join(
            clean(fields.get(f"StoryTitle{i}", "")) for i in selected
        )
        or None,
        "substory_match_status": status,
        "appearance_scope": "selected_narrative" if selected else "whole_issue_unresolved",
        "appearance_indexed_sections": sum(
            any(row["role"] != "locations" for row in indexed_appearances[i])
            for i in appearance_indexes
        ),
    }
    result.update(indexed_credits(fields, selected, indexes))
    self_inking = []
    writer_artist_overlap = []
    for index in selected:
        credits = indexed_credits(fields, [index], indexes)
        writers = set((credits["narrative_writers"] or "").split("|")) - {""}
        pencils = set((credits["narrative_pencilers"] or "").split("|")) - {""}
        inks = set((credits["narrative_inkers"] or "").split("|")) - {""}
        if writers and pencils:
            writer_artist_overlap.append(bool(writers & pencils))
        if pencils and inks:
            self_inking.append(len(pencils & inks) / len(pencils))
    result["_writer_artist_overlap_share"] = (
        sum(writer_artist_overlap) / len(writer_artist_overlap) if writer_artist_overlap else None
    )
    result["_self_inking_share"] = sum(self_inking) / len(self_inking) if self_inking else None
    for role in ["featured", "supporting", "antagonists", "other", "locations"]:
        subset = {
            r["id"]: r["name"] for r in entities if r["role"] == role and r["mode"] == "ordinary"
        }
        result[f"{role}_entity_ids"] = "|".join(sorted(subset)) or None
        result[f"{role}_entity_names"] = "|".join(subset[k] for k in sorted(subset)) or None
    for mode in MODES[:-1]:
        result[f"{mode}_entity_ids"] = (
            "|".join(
                sorted(
                    {r["id"] for r in entities if r["mode"] == mode and r["role"] != "locations"}
                )
            )
            or None
        )
    character_entities = {
        r["id"] for r in entities if r["role"] != "locations" and r["mode"] == "ordinary"
    }
    result["ordinary_cast_entity_count"] = (
        len(character_entities) if result["appearance_indexed_sections"] else None
    )
    result["character_universe_qualifiers"] = (
        "|".join(
            sorted(
                {
                    m[1]
                    for target in character_entities
                    if (m := re.search(r"\(([^()]+)\)$", target))
                }
            )
        )
        or None
    )
    collections = collection_targets(fields, selected, len(indexes))
    result["collection_titles"] = "|".join(collections) or None
    result["collection_urls"] = (
        "|".join("https://dc.fandom.com/wiki/" + quote(t.replace(" ", "_")) for t in collections)
        or None
    )
    result["collection_link_scope"] = (
        "issue_notes_may_reference_other_substories" if collections else None
    )
    return result


def union_values(rows, key):
    return sorted({v for row in rows for v in (row.get(key) or "").split("|") if v})


def team_features(rows, total):
    """Teams are sets of credited writers and pencilers, equally weighted per issue."""
    teams = []
    matched_teams = []
    self_ink, writer_artist = [], []
    for row in rows:
        writers = set((row["narrative_writers"] or "").split("|")) - {""}
        artists = set((row["narrative_pencilers"] or "").split("|")) - {""}
        inkers = set((row["narrative_inkers"] or "").split("|")) - {""}
        team = (tuple(sorted(writers)), tuple(sorted(artists))) if writers and artists else None
        teams.append(team)
        if team:
            matched_teams.append(team)
            if row.get("_writer_artist_overlap_share") is not None:
                writer_artist.append(row["_writer_artist_overlap_share"])
            elif "_writer_artist_overlap_share" not in row:
                writer_artist.append(bool(writers & artists))
        if row.get("_self_inking_share") is not None:
            self_ink.append(row["_self_inking_share"])
        elif "_self_inking_share" not in row and artists and inkers:
            self_ink.append(len(artists & inkers) / len(artists))
    counts = collections.Counter(matched_teams)
    adjacent = [(a, b) for a, b in zip(teams, teams[1:]) if a is not None and b is not None]
    return {
        "narrative_credit_issue_coverage": len(matched_teams) / total,
        "narrative_team_count": len(counts) if counts else None,
        "narrative_dominant_team_share": max(counts.values()) / len(matched_teams)
        if counts
        else None,
        "narrative_team_switch_count": sum(a != b for a, b in adjacent) if adjacent else None,
        "narrative_team_comparable_transitions": len(adjacent),
        "narrative_writer_artist_overlap_share": sum(writer_artist) / len(writer_artist)
        if writer_artist
        else None,
        "narrative_self_inking_share": sum(self_ink) / len(self_ink) if self_ink else None,
        "narrative_inking_issue_coverage": len(self_ink) / total,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Accepted for consistency; this enrichment always uses the saved snapshot",
    )
    parser.parse_args()
    stories = pd.read_csv(ROOT / "data/processed/stories.csv")
    issues = pd.read_csv(ROOT / "data/processed/issues.csv")
    pages = wiki_pages(Fetcher(offline=True), issues.lookup_title.dropna().unique().tolist())
    parsed = {title: fields_for(page) for title, page in pages.items()}
    path = ROOT / "references/substory_overrides.json"
    overrides = json.loads(path.read_text()) if path.exists() else {}
    output = {"stories": [], "issues": []}
    for story in stories.itertuples():
        refs = issues[issues.story_id == story.story_id]
        rows = []
        for issue in refs.itertuples():
            override_record = overrides.get(story.story_id, {}).get(issue.requested_title)
            override = override_record["indexes"] if override_record else None
            row = enrich_issue(story, issue, parsed.get(issue.lookup_title, {}), override)
            row["substory_match_note"] = override_record["reason"] if override_record else None
            row["substory_match_source_url"] = (
                override_record["source_url"] if override_record else None
            )
            rows.append(row)
            output["issues"].append({k: v for k, v in row.items() if not k.startswith("_")})
        result = {"story_id": story.story_id, **team_features(rows, len(refs))}
        for key in [
            *[f"narrative_{role}" for role in NARRATIVE_ROLES],
            *[
                f"{role}_entity_ids"
                for role in ["featured", "supporting", "antagonists", "other", "locations"]
            ],
            *[f"{mode}_entity_ids" for mode in MODES[:-1]],
            "character_universe_qualifiers",
            "collection_titles",
            "collection_urls",
        ]:
            result[key] = "|".join(union_values(rows, key)) or None
        for role in ["featured", "supporting", "antagonists", "other", "locations"]:
            result[f"{role}_entity_count"] = (
                len(union_values(rows, f"{role}_entity_ids"))
                if any(r["appearance_indexed_sections"] for r in rows)
                else None
            )
        result["cast_issue_coverage"] = sum(
            bool(r["appearance_indexed_sections"]) for r in rows
        ) / len(refs)
        result["cast_scope"] = (
            "selected_narratives"
            if all(r["appearance_scope"] == "selected_narrative" for r in rows)
            else "includes_whole_issue_unresolved"
        )
        result["substory_attribution_coverage"] = sum(
            r["appearance_scope"] == "selected_narrative" for r in rows
        ) / len(refs)
        result["multi_substory_issue_count"] = sum(r["indexed_substory_count"] > 1 for r in rows)
        result["collection_count"] = len(union_values(rows, "collection_titles"))
        result["collection_scope"] = (
            "issue_notes_may_reference_other_substories" if result["collection_count"] else None
        )
        discussion = pd.to_datetime(story.discussion_date, errors="coerce")
        publication = pd.to_numeric(refs.publication_year, errors="coerce").dropna()
        cover = pd.to_numeric(refs.cover_year, errors="coerce").dropna()
        result["publication_age_year_proxy"] = (
            int(discussion.year - publication.min())
            if pd.notna(discussion) and len(publication) == len(refs)
            else None
        )
        result["cover_age_year_proxy"] = (
            int(discussion.year - cover.min())
            if pd.notna(discussion) and len(cover) == len(refs)
            else None
        )
        output["stories"].append(result)
    assert len(output["stories"]) == len(stories) and len(output["issues"]) == len(issues)
    assert all(0 <= row["substory_attribution_coverage"] <= 1 for row in output["stories"])
    (ROOT / "data/external/enrichment.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False)
    )
    summary = pd.DataFrame(output["stories"])
    print(
        json.dumps(
            {
                "stories": len(summary),
                "fully_attributed": int(summary.substory_attribution_coverage.eq(1).sum()),
                "cast_available": int(summary.featured_entity_ids.notna().sum()),
                "collections_available": int(summary.collection_count.gt(0).sum()),
                "age_proxy_available": int(summary.cover_age_year_proxy.notna().sum()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
