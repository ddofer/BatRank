"""Official Eisner/Kirby winner records and temporally explicit story-level features.

Run ``python -m scripts.awards [--offline]``. Sources are fetched serially once;
all joins use creator names/explicit work matches, never title similarity.
"""

import argparse
import hashlib
import json
import re
import time
import unicodedata
from datetime import datetime, timezone

import pandas as pd
from bs4 import BeautifulSoup

from scripts.dataset import Fetcher, ROOT

RAW = ROOT / "data/raw/awards"
DEST = ROOT / "data/external/awards.json"
BASE = "https://www.comic-con.org/awards/eisner-awards/past-recipients/"
SOURCES = {
    decade: BASE
    + f"past-{('recipenties' if decade in ('2010s', '2020s') else 'recipients')}-{decade}/"
    for decade in ["1980s", "1990s", "2000s", "2010s", "2020s"]
}
ROLES = ["writers", "pencilers", "inkers", "colorists", "letterers", "editors"]
ALIASES = {
    "Dave Mazzucchelli": ["David Mazzucchelli"],
    "Dennis O'Neil": ["Denny O'Neil"],
    "Sean Murphy": ["Sean Gordon Murphy"],
    "J.M. DeMatteis": ["J. M. DeMatteis"],
    "J.H. Williams III": ["J. H. Williams III"],
    "J. Bone": ["J Bone"],
    "David Finch": ["Dave Finch"],
    "Brian K. Vaughan": ["Brian Vaughan"],
    "Jose Marzan, Jr.": ["Jose Marzan Jr.", "José Marzán, Jr.", "José Marzán Jr."],
    "Sergio Aragones": ["Sergio Aragonés"],
    "Laura Martin": ["Laura DePuy", "Laura Dupuy", "Laura DePuy [Martin]", "Laura Dupuy [Martin]"],
}
PERSONAL_CATEGORIES = re.compile(
    r"^(?:Best (?:Writer|Artist|Pencill|Inker|Color|Letter|Cover Artist|Painter|Editor)|Talent Deserving)",
    re.I,
)
CATEGORY = re.compile(
    r"(?:Best [^:]{1,100}|Hall of Fame|Talent Deserving of Wider Recognition)\s*:"
)


def normalize(name):
    name = unicodedata.normalize("NFKD", name.replace("’", "'"))
    return re.sub(
        r"[^a-z0-9]", "", "".join(c for c in name if not unicodedata.combining(c)).lower()
    )


def names(value):
    return set(str(value).split("|")) if pd.notna(value) and str(value) else set()


def creator_index(stories):
    creators = sorted(set().union(*(names(v) for role in ROLES for v in stories[role])))
    types_path = ROOT / "references/creator_entity_types.json"
    aliases_path = ROOT / "references/creator_aliases.json"
    nonpeople = set(json.loads(types_path.read_text())) if types_path.exists() else set()
    redirects = json.loads(aliases_path.read_text()) if aliases_path.exists() else {}
    result = {}
    for name in creators:
        if redirects.get(name, name) in nonpeople:
            continue
        for variant in [name, *ALIASES.get(name, [])]:
            result.setdefault(normalize(variant), name)
    # Initial spacing, punctuation, accents and curly apostrophes are normalized.
    return result


def match_creators(text, index):
    """Match whole names; prevent e.g. Tim Sale matching a fragment of a surname."""
    words = re.findall(r"[\w’'.-]+", text, flags=re.UNICODE)
    found = set()
    for length in range(1, 6):
        for start in range(len(words) - length + 1):
            key = normalize(" ".join(words[start : start + length]))
            if key in index:
                found.add(index[key])
    return sorted(found)


def winning_roles(category):
    category = category.lower()
    if "writer/artist" in category or "writer-artist" in category:
        return ["writers", "pencilers"]
    if "writer" in category:
        return ["writers"]
    if "pencill" in category:
        return ["pencilers", "inkers"]
    if "inker" in category:
        return ["inkers"]
    if "color" in category:
        return ["colorists"]
    if "letter" in category:
        return ["letterers"]
    if "cover" in category:
        return ["cover_artists"]
    if "editor" in category:
        return ["editors"]
    if "artist" in category or "painter" in category:
        return ["pencilers"]
    return []


def parse_winners(html, url, index):
    soup = BeautifulSoup(html, "html.parser")
    content = soup.select_one(".entry-content")
    if content is None:
        raise ValueError(f"Winner content missing: {url}")
    year, system, rows, years = None, None, [], set()
    for element in content.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "li"]):
        text = element.get_text(" ", strip=True).replace("\xa0", " ")
        if element.name != "li":
            heading = re.match(r"(\d{4}) (Eisner|Kirby) Awards", text)
            if heading:
                year, system = int(heading[1]), heading[2]
                years.add(year)
            continue
        if year is None or element.find_parent("li") is not None:
            continue
        # The official 1998 archive puts two winners in one list item.
        matches = list(CATEGORY.finditer(text))
        for position, match in enumerate(matches):
            category = match[0].rstrip(":").strip()
            body = text[
                match.end() : matches[position + 1].start() if position + 1 < len(matches) else None
            ].strip()
            if not body:
                following = element.find_next_sibling("li")
                if following is not None and not CATEGORY.search(
                    following.get_text(" ", strip=True)
                ):
                    body = following.get_text(" ", strip=True)
                if not body:
                    raise ValueError(f"Empty winner: {year} {category}")
            kind = (
                "honor"
                if category == "Hall of Fame"
                else ("personal" if PERSONAL_CATEGORIES.search(category) else "work")
            )
            if kind == "personal":
                # Recipient names precede their credited books. Ties on these
                # winner lists are separated by a bullet or the literal 'and'.
                chunks = re.split(r"\s*[•●]\s*|;\s+and\s+|\)\s+and\s+", body)
                recipient_text = " and ".join(chunk.split(",", 1)[0] for chunk in chunks)
                matched = match_creators(recipient_text, index)
                # A few joint artist winners use a slash or 'and' before books.
                # Names after a comma are permitted only before the first italic
                # book title; the source HTML is checked below for that region.
                first_book = next(
                    (
                        tag.get_text(" ", strip=True)
                        for tag in element.find_all(["em", "i"])
                        if tag.get_text(strip=True)
                    ),
                    None,
                )
                before_book = (
                    body.split(first_book, 1)[0]
                    if first_book and first_book in body
                    else body.split(",", 1)[0]
                )
                matched = sorted(set(matched) | set(match_creators(before_book, index)))
            elif kind == "honor":
                matched = match_creators(body, index)
            else:
                matched = []
            event_id = hashlib.sha256(f"{system}|{year}|{category}|{body}".encode()).hexdigest()[
                :12
            ]
            rows.append(
                dict(
                    event_id=event_id,
                    award=system,
                    award_year=year,
                    category=category,
                    recipient_scope=kind,
                    recipient_names=matched,
                    winning_roles=winning_roles(category),
                    awarded_work=(
                        body.split(",", 1)[1].strip()
                        if kind == "personal" and "," in body
                        else body
                        if kind == "work"
                        else ""
                    ),
                    winner_description=body,
                    source_url=url,
                )
            )
    if not rows:
        raise ValueError(f"No awards parsed: {url}")
    return rows, sorted(years)


# Work matching is intentionally explicit: award-level facts have different scopes.
# The tuple names a ranked story, award year/category, and the relationship to it.
WORK_MATCHES = [
    (
        "5bbf6ce8186b",
        1999,
        "Best Title for a Younger Audience",
        "series_context",
        "Lucky Day appeared in the 1998 Gotham Adventures title recognized for its eligible-year output; no individual-story award.",
    ),
    (
        "070120d8772c",
        1999,
        "Best Title for a Younger Audience",
        "series_context",
        "Polar Opposites appeared in the 1998 Gotham Adventures title; series recognition, not an individual-story award.",
    ),
    (
        "5896d824488b",
        1999,
        "Best Title for a Younger Audience",
        "series_context",
        "Last Chance appeared in the 1998 Gotham Adventures title; series recognition, not an individual-story award.",
    ),
    (
        "f9c5c2dcb93d",
        1996,
        "Best Title for Younger Readers",
        "series_context",
        "A Christmas Riddle appeared in Batman and Robin Adventures #3, published in 1995 (January 1996 cover date); the series won, not this specific story.",
    ),
    (
        "ab7bdfcb16cd",
        1998,
        "Best Limited Series",
        "exact_work",
        "The complete 13-issue Long Halloween series.",
    ),
    (
        "ab7bdfcb16cd",
        1999,
        "Best Graphic Album–Reprint",
        "collected_edition",
        "Collected edition of the ranked series; edition award, not an additional original-series award.",
    ),
    ("968a68810ffc", 1997, "Best Limited Series", "exact_work", "Kingdom Come #1–4."),
    (
        "968a68810ffc",
        1998,
        "Best Publication Design",
        "edition_design",
        "Deluxe slipcover edition; design recognition is distinct from story recognition.",
    ),
    (
        "f23610ee97c3",
        1997,
        "Best Anthology",
        "exact_work",
        "Original Batman: Black and White four-issue anthology.",
    ),
    (
        "f23610ee97c3",
        1997,
        "Best Short Story",
        "contained_story",
        "Heroes is one short story in anthology issue #4; the anthology as a whole did not win this category.",
    ),
    (
        "f8770a6ab230",
        1989,
        "Best Graphic Album",
        "exact_work",
        "Batman: The Killing Joke original graphic novel.",
    ),
    ("ef9601903ded", 1994, "Best Single Issue", "exact_work", "Batman Adventures: Mad Love."),
    ("af75d1bbceb1", 1995, "Best Single Issue", "exact_work", "Batman Adventures Holiday Special."),
    ("49ca644a0d4c", 2007, "Best Limited Series", "exact_work", "Batman: Year 100 #1–4."),
    (
        "57b25facd099",
        2007,
        "Best Single Issue (or One-Shot)",
        "exact_work",
        "Batman/The Spirit #1, Crime Convention.",
    ),
    ("d9d84232e2a9", 2005, "Best Limited Series", "exact_work", "DC: The New Frontier #1–6."),
    (
        "d9d84232e2a9",
        2007,
        "Best Graphic Album–Reprint",
        "collected_edition",
        "Absolute edition of DC: The New Frontier.",
    ),
    (
        "d9d84232e2a9",
        2007,
        "Best Publication Design",
        "edition_design",
        "Absolute edition design, distinct from narrative recognition.",
    ),
    (
        "9cdc208257ef",
        2004,
        "Best Serialized Story",
        "exact_work",
        "Gotham Central #6–10: Half a Life.",
    ),
    (
        "fc7076357f61",
        2003,
        "Best Publication Design",
        "edition_design",
        "Batman: Nine Lives design by Amie Brockway-Metcalf.",
    ),
    (
        "150e380a6b21",
        2002,
        "Best Graphic Album–Reprint",
        "collected_edition",
        "Collected edition of Dark Victory.",
    ),
    (
        "31021b9d4547",
        2023,
        "Best Short Story",
        "contained_story",
        "Finding Batman is a short story in the ranked DC Pride 2022 anthology.",
    ),
    (
        "c1754cfe9f72",
        2025,
        "Best Archival Collection/Project—Comic Books",
        "archival_edition",
        "David Mazzucchelli Batman Year One Artist’s Edition; original story versus reproduction edition differ.",
    ),
    (
        "c1754cfe9f72",
        2025,
        "Best Publication Design",
        "edition_design",
        "Year One Artist’s Edition design by Chip Kidd, not the original comic’s design.",
    ),
]


def year_before(event, cutoff):
    return pd.notna(cutoff) and event["award_year"] < int(cutoff)


def enrich(stories, events, narrative=None, complete_publication_years=None):
    by_id = {str(row.story_id): row for row in stories.itertuples()}
    index = creator_index(stories)
    narrative = narrative or {}
    work = {}
    for story_id, year, category, scope, note in WORK_MATCHES:
        if story_id not in by_id:
            raise ValueError(f"Missing ranked work: {story_id}")
        candidates = [
            event
            for event in events
            if event["award"] == "Eisner"
            and event["award_year"] == year
            and event["category"] == category
        ]
        if len(candidates) != 1:
            raise ValueError(f"Award match not unique: {year} {category}: {len(candidates)}")
        work.setdefault(story_id, []).append(
            dict(event_id=candidates[0]["event_id"], scope=scope, note=note)
        )
    result = {}
    for story_id, story in by_id.items():
        selected = narrative.get(story_id, {})
        selected_complete = (
            selected.get("substory_attribution_coverage") == 1
            and selected.get("narrative_credit_issue_coverage") == 1
        )
        role_names = {
            role: {
                index.get(normalize(name), name)
                for name in names(selected.get(f"narrative_{role}"))
                if selected_complete
            }
            if selected_complete
            else {index.get(normalize(name), name) for name in names(getattr(story, role))}
            for role in ROLES
        }
        crew = set().union(*role_names.values())
        personal = [
            event
            for event in events
            if event["award"] == "Eisner"
            and event["recipient_scope"] == "personal"
            and crew.intersection(event["recipient_names"])
        ]
        honors = [
            event
            for event in events
            if event["award"] == "Eisner"
            and event["recipient_scope"] == "honor"
            and crew.intersection(event["recipient_names"])
        ]
        kirby = [
            event
            for event in events
            if event["award"] == "Kirby"
            and event["recipient_scope"] == "personal"
            and crew.intersection(event["recipient_names"])
        ]
        actual_publication = (
            complete_publication_years.get(story_id)
            if complete_publication_years is not None
            else story.publication_year_start
        )
        publication = actual_publication if pd.notna(actual_publication) else story.cover_year_start
        discussion = (
            int(str(story.discussion_date)[:4]) if pd.notna(story.discussion_date) else None
        )
        prior_observed = pd.notna(publication) and publication > 1988
        row = dict(
            awards_coverage_status="official_winners_1985_2025;Eisner_since_1988;no_1990_ceremony;reviewed_work_matches_only",
            awards_credit_scope="selected_narratives"
            if selected_complete
            else "whole_issue_credits_fallback",
            awards_creator_matching_status="credited_names_reviewed" if crew else "missing_credits",
            awards_credited_creator_count=len(crew),
            creator_eisner_personal_award_holders_pre_publication=len(
                crew.intersection(
                    n for e in personal if year_before(e, publication) for n in e["recipient_names"]
                )
            )
            if prior_observed
            else None,
            awards_prepublication_coverage=(
                "observed_since_1988" if prior_observed else "award_not_started_or_unknown_date"
            ),
            awards_prepublication_observed_years=sum(
                1988 <= year < publication for year in range(1988, 2026) if year != 1990
            )
            if pd.notna(publication)
            else None,
            awards_publication_year_basis="publication_year"
            if pd.notna(actual_publication)
            else ("cover_year_proxy" if pd.notna(story.cover_year_start) else "unknown"),
            creator_eisner_personal_wins_total=len(personal),
            creator_eisner_personal_wins_pre_publication=sum(
                year_before(e, publication) for e in personal
            )
            if prior_observed
            else None,
            creator_eisner_personal_wins_pre_discussion=sum(
                year_before(e, discussion) for e in personal
            )
            if discussion
            else None,
            creator_eisner_personal_wins_after_discussion_year=sum(
                e["award_year"] > discussion for e in personal
            )
            if discussion
            else None,
            creator_eisner_hall_of_fame_total=len(
                crew.intersection(n for e in honors for n in e["recipient_names"])
            ),
            creator_eisner_hall_of_fame_pre_publication=len(
                crew.intersection(
                    n for e in honors if year_before(e, publication) for n in e["recipient_names"]
                )
            )
            if prior_observed
            else None,
            creator_kirby_personal_wins_total=len(kirby),
            creator_award_names="|".join(
                sorted(
                    crew.intersection(
                        n for e in personal + honors + kirby for n in e["recipient_names"]
                    )
                )
            ),
            creator_award_event_ids="|".join(e["event_id"] for e in personal + honors + kirby),
        )
        for role in ["writers", "pencilers", "inkers", "colorists", "letterers"]:
            relevant = [
                e
                for e in personal
                if role in e["winning_roles"]
                and role_names[role].intersection(e["recipient_names"])
            ]
            row[f"{role}_eisner_role_wins_pre_publication"] = (
                sum(year_before(e, publication) for e in relevant) if prior_observed else None
            )
            row[f"{role}_eisner_role_wins_pre_discussion"] = (
                sum(year_before(e, discussion) for e in relevant) if discussion else None
            )
        linked = work.get(story_id, [])
        for scope, label in [
            ("exact_work", "exact_work"),
            ("contained_story", "contained_story"),
            ("collected_edition", "collected_edition"),
            ("edition_design", "edition_design"),
            ("archival_edition", "archival_edition"),
            ("series_context", "series_context"),
        ]:
            row[f"work_eisner_{label}_wins"] = sum(item["scope"] == scope for item in linked)
        event_by_id = {event["event_id"]: event for event in events}
        row["work_eisner_exact_work_wins_pre_discussion"] = (
            sum(
                item["scope"] == "exact_work"
                and year_before(event_by_id[item["event_id"]], discussion)
                for item in linked
            )
            if discussion
            else None
        )
        row["work_eisner_matched_wins_after_discussion_year"] = (
            sum(event_by_id[item["event_id"]]["award_year"] > discussion for item in linked)
            if discussion
            else None
        )
        row["work_awards_match_status"] = (
            "verified_positive" if linked else "not_exhaustively_reviewed"
        )
        row["work_award_matches"] = linked
        result[story_id] = row
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    stories = pd.read_csv(ROOT / "data/processed/stories.csv")
    index = creator_index(stories)
    fetcher, events, years = Fetcher(), [], []
    sources = []
    for decade, url in SOURCES.items():
        path = RAW / f"{decade}.html"
        if not path.exists():
            if args.offline:
                raise FileNotFoundError(path)
            response = fetcher.session.get(url, timeout=90)
            response.raise_for_status()
            path.write_text(response.text)
            time.sleep(2)
        parsed, seen = parse_winners(path.read_text(), url, index)
        events.extend(parsed)
        years.extend(seen)
        sources.append(
            dict(url=url, years=seen, raw_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        )
    assert set(range(1985, 2026)) - {1990} == set(years), sorted(set(years))
    assert len({event["event_id"] for event in events}) == len(events)
    enrichment = ROOT / "data/external/enrichment.json"
    narrative = (
        {row["story_id"]: row for row in json.loads(enrichment.read_text())["stories"]}
        if enrichment.exists()
        else {}
    )
    issue_years = (
        pd.read_csv(ROOT / "data/processed/issues.csv").groupby("story_id").publication_year
    )
    complete_publication_years = {
        story_id: float(years.min()) for story_id, years in issue_years if years.notna().all()
    }
    output = dict(
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        award_years=sorted(set(years)),
        coverage_note="Official Eisner winners 1988–2025 and predecessor Kirby winners 1985–1987. No ceremony in 1990. Personal award recipients matched to credited creator names; selected ranked-work wins explicitly reviewed. Zero means no matched record in this universe, not no prizes of any kind.",
        sources=sources,
        events=events,
        stories=enrich(stories, events, narrative, complete_publication_years),
    )
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    used = {
        event_id
        for row in output["stories"].values()
        for event_id in row["creator_award_event_ids"].split("|")
        if event_id
    }
    used.update(
        item["event_id"] for row in output["stories"].values() for item in row["work_award_matches"]
    )
    records = [
        dict(
            event_id=e["event_id"],
            award=e["award"],
            award_year=e["award_year"],
            category=e["category"],
            recipient_scope=e["recipient_scope"],
            recipient_names="|".join(e["recipient_names"]),
            winning_roles="|".join(e["winning_roles"]),
            awarded_work=e["awarded_work"],
            source_url=e["source_url"],
        )
        for e in events
        if e["event_id"] in used
    ]
    pd.DataFrame(records).to_csv(ROOT / "data/external/award_events.csv", index=False)
    personal = [e for e in events if e["recipient_scope"] == "personal" and e["recipient_names"]]
    print(
        json.dumps(
            dict(
                events=len(events),
                matched_personal_events=len(personal),
                creators=len(set(n for e in personal for n in e["recipient_names"])),
                stories_with_personal_win=sum(
                    s["creator_eisner_personal_wins_total"] > 0 for s in output["stories"].values()
                ),
                work_matches=len(WORK_MATCHES),
            ),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
