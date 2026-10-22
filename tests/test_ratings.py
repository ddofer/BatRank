from types import SimpleNamespace

import pandas as pd
import pytest

from scripts.ratings import goodreads_shelf, issue_rating, roundup_series, story_ratings


def test_goodreads_uses_aggregate_not_contributor_role():
    html = """<div class="elementList"><a class="bookTitle" href="/book/show/59980.Batman">Year One</a>
    <a class="authorName">Frank Miller</a><span class="greyText smallText">(Writer)</span>
    <span class="greyText smallText">avg rating 4.25 — 284,258 ratings — published 1988</span></div>"""
    book = goodreads_shelf(html, "https://www.goodreads.com/shelf/show/batman", "2026-10-21")[59980]
    assert book["goodreads_rating"] == 4.25 and book["goodreads_rating_count"] == 284258
    with pytest.raises(ValueError):
        goodreads_shelf("<html>Access challenge</html>", "url", "2026-10-21")


def test_roundup_keeps_audiences_and_annuals_but_skips_trades():
    def row(token, path="reviews"):
        return f"""<tr><td class="ratingCell">
        <div class="critic-rating"><div class="review"><span>8.4</span></div><div class="review-count">34 Reviews</div></div>
        <div class="user-rating"><div class="review"><span>7.9</span></div><div class="review-count">88 Reviews</div></div></td>
        <td><a href="/comic-books/{path}/dc-comics/batman-(2016)/{token}">{token}</a></td></tr>"""

    parsed = roundup_series(
        row("51") + row("annual-1") + row("vol-8", "trades"), "batman-(2016)", "2026-10-21"
    )
    assert list(parsed) == ["51", "annual-1"]
    assert parsed["51"]["roundup_user_count"] == 88
    assert parsed["51"]["roundup_critic_rating"] == 8.4
    missing = row("51").replace("8.4", "N/A")
    assert (
        "roundup_critic_rating" not in roundup_series(missing, "batman-(2016)", "2026-10-21")["51"]
    )


def test_detective_resumed_numbering_and_credit_conflict():
    issue = SimpleNamespace(
        wiki_title="Detective Comics Vol 1 934",
        writers="James Tynion IV",
        pencilers="Eddy Barrows",
        inkers="Eber Ferreira",
    )
    catalogues = {
        "detective-comics-(2016)": {
            "934": {"roundup_user_rating": 8.1, "creators": ["James Tynion IV"]}
        }
    }
    result = issue_rating(issue, {"Detective Comics Vol 1": "detective-comics"}, catalogues)
    assert result["roundup_credit_check"] == "overlap"
    catalogues["detective-comics-(2016)"]["934"]["creators"] = ["An unrelated creator"]
    assert (
        issue_rating(issue, {"Detective Comics Vol 1": "detective-comics"}, catalogues)[
            "roundup_credit_check"
        ]
        == "conflict"
    )


def test_partial_coverage_is_not_complete_and_count_is_not_people():
    stories = pd.DataFrame(
        [dict(story_id="a", cover_year_start=2016, source_label="A", issue_list_complete=True)]
    )
    issues = pd.DataFrame(
        [dict(story_id="a", wiki_title="Batman Vol 3 " + str(n)) for n in [1, 2, 3]]
    )
    ratings = pd.DataFrame(
        [
            dict(
                wiki_title="Batman Vol 3 1",
                roundup_user_rating=8.0,
                roundup_user_count=100,
                roundup_critic_rating=9.0,
                roundup_critic_count=2,
            ),
            dict(wiki_title="Batman Vol 3 2", roundup_user_rating=6.0, roundup_user_count=20),
        ]
    )
    result = story_ratings(stories, issues, ratings).iloc[0]
    assert result.roundup_user_rating == 7.0  # Equal issue weights, not vote weights.
    assert result.roundup_user_count == 120 and result.roundup_user_min_count == 20
    assert result.roundup_user_coverage == 2 / 3 and not result.roundup_user_complete


def test_duplicate_issue_number_is_ambiguous_not_last_wins():
    row = """<tr><td class="ratingCell"><div class="user-rating"><div class="review"><span>8.0</span></div><div class="review-count">5 Reviews</div></div></td><td><a href="/comic-books/reviews/dc-comics/batwoman-(2010)/0">0</a></td></tr>"""
    assert roundup_series(row + row, "batwoman-(2010)", "2026-10-21") == {}


def test_empty_http_success_is_not_cached(tmp_path, monkeypatch):
    from scripts.ratings import fetch_html
    from urllib.robotparser import RobotFileParser

    robots = RobotFileParser()
    robots.parse(["User-agent: *", "Allow: /"])
    response = SimpleNamespace(status_code=202, content=b"", text="", raise_for_status=lambda: None)
    session = SimpleNamespace(
        headers={"User-Agent": "BatChatDataset"}, get=lambda *a, **k: response
    )
    monkeypatch.setattr("scripts.ratings.time.sleep", lambda seconds: None)
    path = tmp_path / "response.html"
    with pytest.raises(ValueError, match="Empty/challenged"):
        fetch_html(session, "https://www.goodreads.com/book/show/1", path, robots, False)
    assert not path.exists()


def test_numbered_annual_can_match_the_rated_story():
    html = """<tr><td class="ratingCell"><div class="user-rating">
    <div class="review"><span>9.6</span></div><div class="review-count">80 Reviews</div>
    </div></td><td><a href="/comic-books/reviews/dc-comics/batman-(2016)/annual-2">2</a>
    <a href="/comic-books/writer-artist/tom-king">Tom King</a></td></tr>"""
    catalogue = roundup_series(html, "batman-(2016)", "2026-10-22")
    issue = SimpleNamespace(
        wiki_title="Batman Annual Vol 3 2", writers="Tom King", pencilers="Lee Weeks", inkers=None
    )
    result = issue_rating(
        issue, {"Batman Annual Vol 3": "batman-(2016)"}, {"batman-(2016)": catalogue}
    )
    assert result["roundup_user_rating"] == 9.6
    assert result["roundup_credit_check"] == "overlap"


def test_goodreads_book_uses_public_aggregate():
    from scripts.ratings import goodreads_book

    html = """<script type="application/ld+json">{"@type":"Book","name":"Example",
    "author":[{"name":"A Writer"}],"aggregateRating":{"ratingValue":4.1,"ratingCount":1200}}
    </script>"""
    result = goodreads_book(html, "https://www.goodreads.com/book/show/1", "2026-10-22")
    assert result["goodreads_rating"] == 4.1 and result["goodreads_rating_count"] == 1200
    assert result["goodreads_author"] == "A Writer"
    with pytest.raises(ValueError, match="No public book aggregate"):
        goodreads_book("<html>Challenge</html>", "url", "date")


def test_named_special_requires_an_explicit_issue_match():
    issue = SimpleNamespace(
        wiki_title="Batman: One Bad Day - The Riddler Vol 1 1",
        writers="Tom King",
        pencilers="Mitch Gerads",
        inkers=None,
    )
    row = {"roundup_user_rating": 8.4, "creators": ["Tom King"]}
    catalogues = {"batman-one-bad-day-(2022)": {"the-riddler-1": row}}
    assert issue_rating(issue, {}, catalogues) is None
    matches = {issue.wiki_title: {"slug": "batman-one-bad-day-(2022)", "token": "the-riddler-1"}}
    assert issue_rating(issue, {}, catalogues, matches)["roundup_user_rating"] == 8.4
