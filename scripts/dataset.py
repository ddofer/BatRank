"""Fetch a cached, serial snapshot; export story and issue tables. Run from the project root."""

import argparse
import hashlib
import json
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote

import mwparserfromhell
import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"
RANKINGS = "https://comicsxf.com/batchat-rankings/"
API = "https://dc.fandom.com/api.php"
ROLES = {
    "writers": "Writer",
    "pencilers": "Penciler",
    "inkers": "Inker",
    "colorists": "Colorist",
    "letterers": "Letterer",
    "editors": "Editor",
    "cover_artists": "CoverArtist",
    "executive_editors": "Executive Editor",
}


def clean(value):
    code = mwparserfromhell.parse(str(value))
    for link in list(code.filter_wikilinks()):
        if str(link.title).lower().startswith(("file:", "image:", "category:")):
            code.remove(link)
    return " ".join(code.strip_code().split())


def parse_rankings(html):
    content = BeautifulSoup(html, "html.parser").select_one(".entry-content")
    if content is None:
        raise ValueError("Rankings content missing; HTML structure may have changed")
    rows = []
    for h in content.find_all("h2"):
        if not h.get_text(strip=True).isdigit():
            continue
        rank = int(h.get_text(strip=True))
        siblings = []
        for item in h.next_siblings:
            if getattr(item, "name", None) == "h2" and item.get_text(strip=True).isdigit():
                break
            siblings.append(str(item))
        block = BeautifulSoup("".join(siblings), "html.parser")
        title = block.find("h2").get_text(" ", strip=True)
        issue = block.find("li").get_text(" ", strip=True)
        image = block.find("img")
        rows.append(
            dict(
                rank=rank,
                source_label=title,
                title=title,
                issues_raw=issue,
                source_year=block.find("h3").get_text(strip=True),
                episode_url=image.find_parent("a")["href"],
                cover_url=image["src"],
            )
        )
    # Some links split a rank and its title into separate anchors; parse complete br-delimited lines.
    for p in content.find_all("p"):
        paragraph = BeautifulSoup(str(p), "html.parser")
        for anchor in paragraph.find_all("a"):
            if re.match(r"^\d+\s*\.?\s+\D", anchor.get_text(" ", strip=True)):
                for br in anchor.find_all("br"):
                    br.decompose()
                anchor.insert_before(paragraph.new_tag("br"))
        for line in re.split(r"<br\s*/?>", str(paragraph)):
            fragment = BeautifulSoup(line, "html.parser")
            label = fragment.get_text(" ", strip=True).replace("\xa0", " ")
            match = re.match(r"^(\d+)\s*\.?\s+(.+)", label)
            if not match:
                continue
            rank, label = int(match[1]), match[2].strip()
            part = re.match(r"^(.*?)\s+\((.*)\)$", label)
            title, issue = (part[1], part[2]) if part else (label, label)
            rows.append(
                dict(
                    rank=rank,
                    source_label=label,
                    title=title,
                    issues_raw=issue,
                    source_year=None,
                    episode_url=(fragment.find("a", href=True) or {}).get("href"),
                    cover_url=None,
                )
            )
    for position, row in enumerate(rows, 1):
        row["source_rank"] = row.pop("rank")
        row["rank"] = position
        row["rank_label_disagrees"] = row["source_rank"] != position
        row["story_id"] = hashlib.sha256(row["source_label"].encode()).hexdigest()[:12]
        row["episode_url"] = (row["episode_url"] or "").replace("www.comicsxf.com", "comicsxf.com")
        date = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", row["episode_url"])
        row["discussion_date"] = "-".join(date.groups()) if date else None
    return rows


def issue_titles(label):
    """Expand only explicit issue references; unnumbered books are looked up by exact title."""
    text = label.replace("’", "'").replace("–", "-").replace("—", "-")
    text = text.replace("#1,000,000", "#1000000").replace("#1,027", "#1027")
    text = re.sub(r"\b(?:Vol\.?|V)\s*\.?\s*(\d+)\.?", r"Vol \1", text, flags=re.I)
    text = text.replace("&", "and")
    # A comma introduces a series only when it is followed by a name, not another issue number.
    chunks = re.split(
        r"(?<=\d),\s*(?=[A-Za-z])|(?<=\d)/\s*(?=[A-Za-z])|(?<=\d)\s+and\s+(?=[A-Za-z])", text
    )
    titles, series, volume = [], None, "1"
    complete = True
    for chunk in chunks:
        chunk = re.sub(r"\s+Back-?[Uu]ps$", "", chunk.strip().rstrip(")"))
        m = re.fullmatch(r"(.+?)\s+#([\d.,\s&and-]+)", chunk)
        if not m:
            complete = False
            continue
        name, numbers = m.groups()
        v = re.search(r"\s+Vol\s+(\d+)\b", name)
        if v:
            volume = v[1]
            name = re.sub(r"\s+Vol\s+\d+\b", "", name).strip()
        if re.fullmatch(r"Vol\s+\d+", name):
            volume = name.split()[-1]
            name = series
        elif not v and not re.match(r"^(Annual|Special)$", name):
            volume = "1"
        if name == "Legends of the Dark Knight":
            name = "Batman: Legends of the Dark Knight"
        if re.match(r"^(Annual|Special)$", name) and series:
            name = series + " " + name
        else:
            series = name.removesuffix(" Annual")
        for token in re.split(r",|\s+and\s+|\s*&\s*", numbers):
            token = token.strip()
            if not token:
                continue
            span = re.fullmatch(r"(\d+)-(\d+)", token)
            if span:
                start, end = map(int, span.groups())
                if not abs(end - start) < 100:
                    raise ValueError(f"Invalid issue range: {label}")
                step = 1 if end >= start else -1
                nums = list(map(str, range(start, end + step, step)))
            elif re.fullmatch(r"\d+(?:\.\d+)?", token):
                nums = [token]
            else:
                complete = False
                continue
            titles.extend(f"{name} Vol {volume} {n}" for n in nums)
    if not titles:
        titles = [re.sub(r"\s+OGN$", "", text).strip()]
    return list(dict.fromkeys(titles)), complete


class Fetcher:
    def __init__(self, offline=False):
        self.offline = offline
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "BatChatDataset/0.1 (public bibliographic research; cached serial requests)"
        )
        retry = Retry(total=3, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))

    def get(self, url, params=None):
        key = hashlib.sha256((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()[:20]
        path = RAW / f"{key}.json"
        if path.exists():
            return json.loads(path.read_text())
        if self.offline:
            raise FileNotFoundError(f"No cached response: {url} {params}")
        time.sleep(2)
        response = self.session.get(url, params=params, timeout=90)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise ValueError(payload["error"])
        path.write_text(json.dumps(payload, ensure_ascii=False))
        return payload


def wiki_pages(fetcher, titles):
    cache = ROOT / "data/interim/wiki_pages.json"
    cache.parent.mkdir(parents=True, exist_ok=True)
    pages = json.loads(cache.read_text()) if cache.exists() else {}
    if not pages:
        for path in sorted(RAW.glob("*.json")):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue  # Initial API probes may have saved an HTML error response.
            query = data.get("query", {}) if isinstance(data, dict) else {}
            saved = query.get("pages", {})
            if not isinstance(saved, dict):
                continue
            by_title = {
                p["title"]: p
                for p in saved.values()
                if "revisions" not in p or "slots" in p["revisions"][0]
            }
            pages.update(by_title)
            redirects = {
                r["from"]: r["to"]
                for key in ("normalized", "redirects")
                for r in query.get(key, [])
            }
            for source in redirects:
                target, seen = source, set()
                while target in redirects and target not in seen:
                    seen.add(target)
                    target = redirects[target]
                if target in by_title:
                    pages[source] = by_title[target]
        cache.write_text(json.dumps(pages, ensure_ascii=False))
    pending = [title for title in titles if title not in pages]
    for start in range(0, len(pending), 50):
        batch = pending[start : start + 50]
        data = fetcher.get(
            API,
            dict(
                action="query",
                titles="|".join(batch),
                prop="revisions|info",
                inprop="url",
                rvprop="content|ids|timestamp",
                rvslots="main",
                redirects=1,
                format="json",
            ),
        )
        query = data["query"]
        by_title = {p["title"]: p for p in query["pages"].values()}
        redirects = {
            r["from"]: r["to"] for k in ("normalized", "redirects") for r in query.get(k, [])
        }
        for title in batch:
            target = title
            seen = set()
            while target in redirects and target not in seen:
                seen.add(target)
                target = redirects[target]
            pages[title] = by_title[target]
        cache.write_text(json.dumps(pages, ensure_ascii=False))
        print(f"Wiki: {min(start + 50, len(pending))}/{len(pending)} lookups", flush=True)
    return {title: pages[title] for title in titles}


def parse_issue(page):
    if "missing" in page or "revisions" not in page:
        return {}
    rev = page["revisions"][0]
    code = mwparserfromhell.parse(rev["slots"]["main"]["*"])
    templates = [t for t in code.filter_templates() if "Comic Template" in str(t.name)]
    if not templates:
        return {}
    fields = {str(p.name).strip(): str(p.value).strip() for p in templates[0].params}
    result = {
        "wiki_title": page["title"],
        "metadata_url": page["fullurl"],
        "issue_id": page["pageid"],
        "revision_id": rev["revid"],
        "revision_timestamp": rev["timestamp"],
    }
    # shortcut: credits include every substory; isolate them before making story-specific creator claims.
    for role, prefix in ROLES.items():
        names = [
            clean(v)
            for k, v in fields.items()
            if re.fullmatch(re.escape(prefix) + r"(?:\d+(?:_\d+)?)?", k) and clean(v)
        ]
        result[role] = "|".join(sorted(set(names))) or None
    result["cover_year"] = clean(fields.get("Year", "")) or None
    result["cover_month"] = clean(fields.get("Month", "")) or None
    result["publication_year"] = clean(fields.get("Pubyear", "")) or None
    result["publication_month"] = clean(fields.get("Pubmonth", "")) or None
    result["publication_day"] = clean(fields.get("Day", "")) or None
    result["page_count"] = clean(fields.get("Pages", fields.get("PageCount", ""))) or None
    synopsis = fields.get("Synopsis1", "")
    # One opening paragraph keeps this compact; it describes the issue's first story, not the full arc.
    result["synopsis_opening"] = next(
        (clean(p) for p in synopsis.split("\n\n") if len(clean(p)) > 80), None
    )
    result["synopsis_opening"] = (result["synopsis_opening"] or "")[:1200] or None
    result["issue_story_titles"] = (
        "|".join(
            clean(v) for k, v in fields.items() if re.fullmatch(r"StoryTitle\d+", k) and clean(v)
        )
        or None
    )
    image = clean(fields.get("Image", ""))
    result["cover_url"] = (
        "https://dc.fandom.com/wiki/Special:Redirect/file/" + quote(image) if image else None
    )
    return result


def attach_snapshot(stories, issues, extra, complete=True):
    """Join a verified source snapshot without accepting stale reference lists or column collisions."""
    rows = extra["stories"]
    if isinstance(rows, dict):
        rows = [dict(story_id=key, **value) for key, value in rows.items()]
    addition = pd.DataFrame(rows)
    assert set(addition.story_id) <= set(stories.story_id)
    if complete:
        assert set(addition.story_id) == set(stories.story_id)
    assert not (set(addition) & set(stories)) - {"story_id"}
    for column in addition:
        if addition[column].map(lambda value: isinstance(value, (dict, list))).any():
            addition[column] = addition[column].map(
                lambda value: (
                    json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else value
                )
            )
    stories = stories.merge(addition, on="story_id", how="left", validate="one_to_one")
    if "issues" in extra:
        addition = pd.DataFrame(extra["issues"])
        keys = ["story_id", "requested_title"]
        incoming, canonical = (
            set(map(tuple, addition[keys].values)),
            set(map(tuple, issues[keys].values)),
        )
        assert incoming <= canonical, "Stale or unknown enriched issue reference"
        if complete:
            assert incoming == canonical, "Missing enriched issue reference"
        assert not (set(addition) & set(issues)) - set(keys)
        issues = issues.merge(addition, on=keys, how="left", validate="one_to_one")
    return stories, issues


def narrative_rating_scope(issues):
    """Align whole-issue ratings only when all wiki-indexed narratives were selected."""
    count = issues.selected_substory_indexes.fillna("").map(
        lambda value: len(str(value).split("|")) if str(value) else 0
    )
    scope = pd.Series("unresolved_issue_scope", index=issues.index)
    resolved = count.gt(0) & issues.indexed_substory_count.gt(0)
    scope.loc[resolved & count.eq(issues.indexed_substory_count)] = "all_indexed_narratives"
    scope.loc[resolved & count.lt(issues.indexed_substory_count)] = "ranked_subset_of_issue"
    return scope


def export(stories, issues, base_only=False):
    watch = pd.read_csv(ROOT / "data/external/creator_watch.csv")
    stories = pd.DataFrame(stories)
    for idx, story in stories.iterrows():
        refs = issues[issues.story_id == story.story_id]
        matched = refs[refs.match_status == "matched_comic_issue"].drop_duplicates("issue_id")
        stories.loc[idx, "issue_reference_count"] = len(refs)
        stories.loc[idx, "matched_issue_count"] = len(matched)
        stories.loc[idx, "metadata_coverage"] = len(matched) / len(refs)
        if (
            len(refs) == len(matched) == 1
            and "#" not in story.issues_raw
            and not re.search(r"Crossover|Arc|et\.al|TPB", story.issues_raw)
        ):
            stories.loc[idx, "issue_list_complete"] = True
            story.issue_list_complete = True
        full = bool(story.issue_list_complete and len(matched) == len(refs))
        stories.loc[idx, "metadata_complete"] = full
        for role in ROLES:
            names = sorted({name for names in matched[role].dropna() for name in names.split("|")})
            stories.loc[idx, role] = "|".join(names) or None
        years = pd.to_numeric(matched.cover_year, errors="coerce").dropna()
        stories.loc[idx, "cover_year_start"] = years.min() if len(years) else None
        stories.loc[idx, "cover_year_end"] = years.max() if len(years) else None
        years = pd.to_numeric(matched.publication_year, errors="coerce").dropna()
        stories.loc[idx, "publication_year_start"] = years.min() if len(years) else None
        stories.loc[idx, "issue_count"] = len(refs) if full else None
        pages = pd.to_numeric(matched.page_count, errors="coerce")
        stories.loc[idx, "page_count"] = pages.sum() if full and pages.notna().all() else None
        stories.loc[idx, "synopsis_opening"] = (
            matched.synopsis_opening.dropna().iloc[0]
            if matched.synopsis_opening.notna().any()
            else None
        )
        stories.loc[idx, "synopsis_source_url"] = (
            matched.loc[matched.synopsis_opening.notna(), "metadata_url"].iloc[0]
            if matched.synopsis_opening.notna().any()
            else None
        )
        if not story.cover_url and matched.cover_url.notna().any():
            stories.loc[idx, "cover_url"] = matched.cover_url.dropna().iloc[0]
        people = {p for role in ROLES for names in matched[role].dropna() for p in names.split("|")}
        flagged = watch[watch.creator.isin(people)]
        stories.loc[idx, "creator_watch_names"] = "|".join(flagged.creator) or None
        stories.loc[idx, "creator_watch_sources"] = "|".join(flagged.source_url) or None
        stories.loc[idx, "creator_watch_status"] = (
            "documented_event_in_issue_credits" if len(flagged) else "unreviewed"
        )
        stories.loc[idx, "creator_watch_count"] = len(flagged)
        label = story.source_label
        medium = (
            "webcomic"
            if ("Wayne Family" in label or "Red Hood: Outlaws" in label)
            else "manga"
            if ("Operation Joker" in label or "Batmanga" in label)
            else "comic"
            if len(matched)
            else "unknown"
        )
        stories.loc[idx, "medium"] = medium
        stories.loc[idx, "format_hint"] = (
            "original_graphic_novel" if "OGN" in label else "unspecified"
        )
    stories["rank_percentile"] = (stories["rank"] - 1) / (len(stories) - 1)
    stories["credit_scope"] = "whole_issue_including_backups"
    stories["synopsis_scope"] = "opening_of_first_available_issue_first_story"
    stories["snapshot_date"] = (
        datetime.fromtimestamp((RAW / "rankings.html").stat().st_mtime, timezone.utc)
        .date()
        .isoformat()
    )
    stories["ranking_source_url"] = RANKINGS
    ratings_path = ROOT / "data/external/ratings.json"
    if ratings_path.exists() and not base_only:
        ratings = json.loads(ratings_path.read_text())
        story_ratings = pd.DataFrame(ratings["stories"])
        assert set(story_ratings.story_id) == set(stories.story_id)
        stories = stories.merge(story_ratings, on="story_id", how="left", validate="one_to_one")
        issues = issues.merge(
            pd.DataFrame(ratings["issues"]), on="wiki_title", how="left", validate="many_to_one"
        )
        assert stories.goodreads_rating.dropna().between(1, 5).all()
        for audience in ["critic", "user"]:
            assert stories[f"roundup_{audience}_rating"].dropna().between(0, 10).all()
            assert stories[f"roundup_{audience}_coverage"].between(0, 1).all()
    for filename in [] if base_only else ["enrichment.json", "awards.json", "catalogue.json"]:
        path = ROOT / "data/external" / filename
        if not path.exists():
            continue
        extra = json.loads(path.read_text())
        stories, issues = attach_snapshot(
            stories, issues, extra, complete=filename != "catalogue.json"
        )
    if "selected_substory_indexes" in issues:
        issues["roundup_narrative_scope"] = narrative_rating_scope(issues)
        scope = issues.groupby("story_id").roundup_narrative_scope.agg(
            lambda values: (
                "unresolved_issue_scope"
                if "unresolved_issue_scope" in set(values)
                else "ranked_subset_of_issue"
                if "ranked_subset_of_issue" in set(values)
                else "all_indexed_narratives"
            )
        )
        stories["roundup_narrative_scope"] = stories.story_id.map(scope)
    assert stories.story_id.is_unique and stories.title.notna().all()
    assert set(issues.story_id) == set(stories.story_id)
    assert stories["rank"].tolist() == list(range(1, len(stories) + 1))
    assert not issues.duplicated(["story_id", "requested_title"]).any()
    assert stories.metadata_coverage.between(0, 1).all()
    assert pd.to_numeric(issues.cover_year, errors="coerce").dropna().between(1930, 2035).all()
    stories.to_csv(OUT / "stories.csv", index=False)
    issues.to_csv(OUT / "issues.csv", index=False)
    coverage = {
        column: {"non_null": int(stories[column].notna().sum()), "total": len(stories)}
        for column in [
            "discussion_date",
            *ROLES,
            "cover_year_start",
            "publication_year_start",
            "issue_count",
            "page_count",
            "synopsis_opening",
            "cover_url",
        ]
    }
    enrichment_columns = [
        "narrative_writers",
        "narrative_pencilers",
        "narrative_colorists",
        "narrative_letterers",
        "featured_entity_ids",
        "antagonists_entity_ids",
        "collection_urls",
        "cover_age_year_proxy",
        "publication_age_year_proxy",
        "creator_eisner_personal_wins_pre_publication",
        "gcd_narrative_page_count",
        "publisher_source_url",
    ]
    report = {
        "stories": len(stories),
        "issue_references": len(issues),
        "matched_references": int(issues.match_status.eq("matched_comic_issue").sum()),
        "fully_enriched_stories": int(stories.metadata_complete.sum()),
        "duplicate_printed_rank_rows": int(stories.source_rank.duplicated(keep=False).sum()),
        "rank_label_disagreements": int(stories.rank_label_disagrees.sum()),
        "coverage": coverage,
        "external_ratings": {
            column: int(stories[column].notna().sum())
            for column in ["goodreads_rating", "roundup_critic_rating", "roundup_user_rating"]
            if column in stories
        },
        "enrichment_coverage": {
            column: int(stories[column].notna().sum())
            for column in enrichment_columns
            if column in stories
        },
        "attribution_scopes": {
            column: stories[column].value_counts().to_dict()
            for column in ["cast_scope", "awards_credit_scope", "roundup_narrative_scope"]
            if column in stories
        },
        "unmatched": issues.loc[
            issues.match_status.eq("unmatched"), ["story_id", "requested_title"]
        ].to_dict("records"),
    }
    (ROOT / "reports/validation.json").write_text(json.dumps(report, indent=2))
    manifest = {
        "ranking_source_url": RANKINGS,
        "snapshot_date": stories.snapshot_date.iloc[0],
        "raw_files_sha256": {
            str(p.relative_to(RAW)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(RAW.rglob("*"))
            if p.is_file()
        },
        "curation_files_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "references").glob("*"))
            if p.suffix in {".csv", ".json"} and p.name != "snapshot.json"
        },
        "processed_files_sha256": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.glob("*.csv"))
        },
    }
    (ROOT / "references/snapshot.json").write_text(json.dumps(manifest, indent=2))
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ("coverage", "unmatched")}, indent=2
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline", action="store_true", help="Rebuild exclusively from cached responses"
    )
    parser.add_argument(
        "--base-only",
        action="store_true",
        help="Rebuild core tables before regenerating enrichments",
    )
    args = parser.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher(args.offline)
    html_path = RAW / "rankings.html"
    if not html_path.exists():
        if args.offline:
            raise FileNotFoundError(html_path)
        response = fetcher.session.get(RANKINGS, timeout=90)
        response.raise_for_status()
        html_path.write_text(response.text)
    stories = parse_rankings(html_path.read_text())
    rss_path = RAW / "podcast.rss"
    if not rss_path.exists() and not args.offline:
        time.sleep(2)
        response = fetcher.session.get(
            "https://feeds.soundcloud.com/users/soundcloud:users:1031972113/sounds.rss", timeout=90
        )
        response.raise_for_status()
        ET.fromstring(response.content)
        rss_path.write_bytes(response.content)
    episode_dates = (
        {
            item.findtext("link"): parsedate_to_datetime(item.findtext("pubDate"))
            .date()
            .isoformat()
            for item in ET.parse(rss_path).findall("./channel/item")
        }
        if rss_path.exists()
        else {}
    )
    overrides = json.loads((ROOT / "references/issue_overrides.json").read_text())
    aliases = json.loads((ROOT / "references/wiki_aliases.json").read_text())
    links = []
    for story in stories:
        story["discussion_date_source"] = "episode_url_path" if story["discussion_date"] else None
        if not story["discussion_date"]:
            story["discussion_date"] = episode_dates.get(story["episode_url"].split("?")[0])
            story["discussion_date_source"] = "podcast_rss" if story["discussion_date"] else None
        if story["source_label"] in overrides:
            titles = overrides[story["source_label"]]["titles"]
            complete = overrides[story["source_label"]]["complete"]
            story["issue_list_note"] = overrides[story["source_label"]]["reason"]
        else:
            titles, complete = issue_titles(story["issues_raw"])
            story["issue_list_note"] = None
        story["issue_list_complete"] = complete
        for title in titles:
            lookup = title
            for source, target in aliases.items():
                if title == source or re.fullmatch(re.escape(source) + r" \d+(?:\.\d+)?", title):
                    suffix = title[len(source) :]
                    lookup = (
                        target.format(issue=suffix.strip())
                        if "{issue}" in target
                        else target + suffix
                    )
                    break
            links.append(
                dict(
                    story_id=story["story_id"],
                    requested_title=title,
                    lookup_title=lookup,
                    lookup_aliased=lookup != title,
                )
            )
    titles = list(dict.fromkeys(link["lookup_title"] for link in links))
    pages = wiki_pages(fetcher, titles)
    issues = pd.DataFrame([{**link, **parse_issue(pages[link["lookup_title"]])} for link in links])
    issues["match_status"] = (
        issues["wiki_title"].notna().map({True: "matched_comic_issue", False: "unmatched"})
    )
    export(stories, issues, base_only=args.base_only)


if __name__ == "__main__":
    main()
