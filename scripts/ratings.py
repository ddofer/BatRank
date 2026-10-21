"""Cache public rating aggregates; run `python -m scripts.ratings [--offline]` before make offline."""

import argparse
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from urllib.robotparser import RobotFileParser

import pandas as pd
from bs4 import BeautifulSoup

from scripts.dataset import RAW, ROOT, Fetcher

CACHE = RAW / "external_ratings"
ROUNDUP = "https://comicbookroundup.com/comic-books/reviews/dc-comics/"
SHELVES = [
    "batman",
    "batman-comics",
    "batman-graphic-novels",
    "catwoman",
    "nightwing",
    "batgirl",
    "gotham-central",
    "dc-comics",
    "batman-and-robin",
    "batman-legends-of-the-dark-knight",
]


def snapshot_date(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date().isoformat()


def fetch_html(session, url, path, robots, offline):
    if not path.exists():
        if offline:
            raise FileNotFoundError(path)
        assert robots.can_fetch(session.headers["User-Agent"], url), url
        time.sleep(max(3, robots.crawl_delay("*") or 0))
        response = session.get(url, timeout=90)
        response.raise_for_status()
        if response.status_code != 200 or len(response.content) < 1000:
            raise ValueError(f"Empty/challenged response; stopped without retrying: {url}")
        path.write_text(response.text)
    if path.stat().st_size < 1000:
        raise ValueError(f"Unusable cached response: {path}")
    return path.read_text()


def goodreads_shelf(html, source_url, retrieved_at):
    books = {}
    for row in BeautifulSoup(html, "html.parser").select(".elementList"):
        link, author = row.select_one("a.bookTitle"), row.select_one("a.authorName")
        stats = next(
            (s for s in row.select("span.greyText.smallText") if "avg rating" in s.text), None
        )
        if not link or not author or not stats:
            continue
        match = re.search(r"avg rating ([\d.]+)\s*[—–-]\s*([\d,]+) ratings", stats.text)
        if not match:
            raise ValueError(f"Unparsed Goodreads aggregate: {stats.text}")
        book_id = int(re.search(r"/show/(\d+)", link["href"])[1])
        score, count = float(match[1]), int(match[2].replace(",", ""))
        assert 1 <= score <= 5 and count > 0
        books[book_id] = dict(
            goodreads_rating=score,
            goodreads_rating_count=count,
            goodreads_title=link.get_text(" ", strip=True),
            goodreads_author=author.get_text(" ", strip=True),
            goodreads_shelf_url=source_url,
            goodreads_retrieved_at=retrieved_at,
        )
    if not books:
        raise ValueError(f"No public shelf aggregates: {source_url}")
    return books


def roundup_series(html, slug, retrieved_at):
    rows = {}
    ambiguous = set()
    for row in BeautifulSoup(html, "html.parser").select("tr"):
        cell = row.select_one(".ratingCell")
        link = row.select_one(f'a[href^="/comic-books/reviews/dc-comics/{slug}/"]')
        if not cell or not link:
            continue
        token = link["href"].rsplit("/", 1)[1]
        # shortcut: annual/special/digital numbering needs explicit edition matching; leave it missing.
        if not re.fullmatch(r"\d+(?:\.\d+)?", token):
            continue
        result = dict(
            roundup_url="https://comicbookroundup.com" + link["href"],
            roundup_catalogue_url=ROUNDUP + slug,
            roundup_retrieved_at=retrieved_at,
        )
        for audience in ["critic", "user"]:
            block = cell.select_one(f".{audience}-rating")
            score = block.select_one(".review span") if block else None
            count = block.select_one(".review-count") if block else None
            if score and score.text.strip() != "N/A":
                value = float(score.text.strip())
                votes = int(re.search(r"[\d,]+", count.text)[0].replace(",", ""))
                assert 0 <= value <= 10 and votes > 0
                result[f"roundup_{audience}_rating"] = value
                result[f"roundup_{audience}_count"] = votes
        result["creators"] = [
            name
            for a in row.select('a[href^="/comic-books/writer-artist/"]')
            for name in a.stripped_strings
        ]
        if token in rows:
            ambiguous.add(token)
        rows[token] = result
    if not rows:
        raise ValueError(f"No numbered issue rows in {slug}")
    # Some catalogues combine restarted numbering or two different #0s under the same URL.
    for token in ambiguous:
        del rows[token]
    return rows


def normalized(name):
    key = re.sub(
        r"[^a-z0-9]",
        "",
        unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower(),
    )
    return {
        "tonysdaniel": "tonydaniel",
        "bryanedwardhill": "bryanhill",
        "nunziodefillipis": "nunziodefilippis",
        "jordanbgorfinkel": "jordangorfinkel",
        "gardnerfrancisfox": "gardnerfox",
        "peterjtomasi": "petertomasi",
        "josluisgarcalpez": "joseluisgarcialopez",
        "richburchett": "rickburchett",
        "michaelcollins": "mikecollins",
        "seangordonmurphy": "seanmurphy",
    }.get(key, key)


def issue_rating(issue, mapping, catalogues):
    if pd.isna(issue.wiki_title):
        return None
    match = re.fullmatch(r"(.+) (\d+(?:\.\d+)?)", issue.wiki_title)
    if not match or match[1] not in mapping:
        return None
    slug = mapping[match[1]]
    if match[1] == "Detective Comics Vol 1" and int(match[2].split(".")[0]) >= 934:
        slug = "detective-comics-(2016)"
    result = catalogues[slug].get(match[2])
    if result is None or not any(k.endswith("_rating") for k in result):
        return None
    result = result.copy()
    creators = result.pop("creators")
    result["roundup_listed_creators"] = "|".join(creators)
    external = {normalized(n) for n in creators}
    wiki = {
        normalized(n)
        for role in [issue.writers, issue.pencilers, issue.inkers]
        if pd.notna(role)
        for n in role.split("|")
    }
    result["roundup_credit_check"] = (
        "overlap" if external & wiki else "conflict" if external and wiki else "unavailable"
    )
    return {"wiki_title": issue.wiki_title, **result}


def story_ratings(stories, issues, ratings):
    joined = issues.merge(ratings, on="wiki_title", how="left", validate="many_to_one")
    rows = []
    for story in stories.itertuples():
        group = joined[joined.story_id.eq(story.story_id)]
        row = dict(story_id=story.story_id)
        proxy = (
            (pd.notna(story.cover_year_start) and story.cover_year_start < 1970)
            or any(
                text in " ".join(group.wiki_title.dropna())
                for text in [
                    "Gotham Knights",
                    "Black and White",
                    "Urban Legends",
                    "Giant",
                    "Annual",
                    "Beyond Unlimited",
                ]
            )
            or bool(re.search(r"back.?up", story.source_label, re.I))
        )
        row["roundup_scope"] = "whole_issue_proxy" if proxy else "listed_issues"
        for audience in ["critic", "user"]:
            column = f"roundup_{audience}_rating"
            rated = group[group[column].notna()]
            row[f"roundup_{audience}_coverage"] = len(rated) / len(group)
            row[f"roundup_{audience}_complete"] = bool(
                len(rated) == len(group) and story.issue_list_complete
            )
            if len(rated):
                row[column] = round(float(rated[column].mean()), 4)
                row[f"roundup_{audience}_count"] = int(rated[f"roundup_{audience}_count"].sum())
                row[f"roundup_{audience}_min_count"] = int(rated[f"roundup_{audience}_count"].min())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    session = Fetcher().session
    robots = {}
    for host, filename in [
        ("https://www.goodreads.com", "goodreads-robots.txt"),
        ("https://comicbookroundup.com", "roundup-robots.txt"),
    ]:
        path = CACHE / filename
        if not path.exists():
            if args.offline:
                raise FileNotFoundError(path)
            response = session.get(host + "/robots.txt", timeout=60)
            response.raise_for_status()
            path.write_text(response.text)
        robots[host] = RobotFileParser()
        robots[host].parse(path.read_text(encoding="utf-8-sig").splitlines())
    books = {}
    for shelf in SHELVES:
        url = "https://www.goodreads.com/shelf/show/" + shelf
        path = CACHE / f"goodreads-shelf-{shelf}.html"
        html = fetch_html(session, url, path, robots["https://www.goodreads.com"], args.offline)
        # Prefer the first encountered public aggregate; do not combine edition/work vote counts.
        for book_id, book in goodreads_shelf(html, url, snapshot_date(path)).items():
            books.setdefault(book_id, book)
    matches = pd.read_csv(ROOT / "references/goodreads_matches.csv")
    goodreads = pd.DataFrame(
        [{**row, **books[row["goodreads_book_id"]]} for row in matches.to_dict("records")]
    )
    goodreads = goodreads.rename(
        columns={"match_scope": "goodreads_match_scope", "match_note": "goodreads_match_note"}
    )
    mapping = json.loads((ROOT / "references/roundup_series.json").read_text())
    catalogues = {}
    for slug in sorted(set(mapping.values()) | {"detective-comics-(2016)"}):
        path = CACHE / f"roundup-series-{slug}.html"
        html = fetch_html(
            session, ROUNDUP + slug, path, robots["https://comicbookroundup.com"], args.offline
        )
        catalogues[slug] = roundup_series(html, slug, snapshot_date(path))
    stories = pd.read_csv(ROOT / "data/processed/stories.csv")
    issues = pd.read_csv(ROOT / "data/processed/issues.csv")
    assert matches.story_id.is_unique and set(matches.story_id) <= set(stories.story_id)
    for match in goodreads.itertuples():
        story = stories.loc[stories.story_id.eq(match.story_id)].iloc[0]
        creators = {
            normalized(n)
            for role in ["writers", "pencilers"]
            if pd.notna(story[role])
            for n in story[role].split("|")
        }
        assert normalized(match.goodreads_author) in creators, (story.title, match.goodreads_author)
    # Inputs may already contain yesterday's export; recompute from the original columns.
    issues = issues.drop(columns=[c for c in issues if c.startswith("roundup_")])
    rows = [
        issue_rating(i, mapping, catalogues)
        for i in issues.drop_duplicates("wiki_title").itertuples()
    ]
    ratings = pd.DataFrame([r for r in rows if r])
    conflicts = ratings[ratings.roundup_credit_check.eq("conflict")]
    ratings = ratings[~ratings.roundup_credit_check.eq("conflict")]
    aggregate = story_ratings(stories, issues, ratings).merge(
        goodreads, on="story_id", how="left", validate="one_to_one"
    )
    assert aggregate.story_id.is_unique and len(aggregate) == len(stories)
    assert ratings.wiki_title.is_unique
    for audience in ["critic", "user"]:
        assert aggregate[f"roundup_{audience}_coverage"].between(0, 1).all()
    payload = {
        "stories": json.loads(aggregate.to_json(orient="records")),
        "issues": json.loads(ratings.to_json(orient="records")),
    }
    destination = ROOT / "data/external/ratings.json"
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    temporary.replace(destination)
    report = dict(
        goodreads_stories=len(goodreads),
        goodreads_scopes=goodreads.goodreads_match_scope.value_counts().to_dict(),
        roundup_issues=len(ratings),
        credit_conflicts=json.loads(conflicts.to_json(orient="records")),
        source_series=len(catalogues),
        aggregation="equal_weight_issue_means; counts are issue-review observations",
        scope="Goodreads same_story matches the named narrative, not every edition's supplementary contents; RoundUp rates whole issues.",
    )
    for audience in ["critic", "user"]:
        report[f"roundup_{audience}_stories"] = int(
            aggregate[f"roundup_{audience}_rating"].notna().sum()
        )
        report[f"roundup_{audience}_complete"] = int(
            aggregate[f"roundup_{audience}_complete"].sum()
        )
    (ROOT / "reports/ratings_validation.json").write_text(
        json.dumps(report, indent=2, allow_nan=False)
    )
    print(json.dumps({k: v for k, v in report.items() if k != "credit_conflicts"}, indent=2))
    print(f"Rejected {len(conflicts)} credit conflicts. Run make offline to attach these features.")


if __name__ == "__main__":
    main()
