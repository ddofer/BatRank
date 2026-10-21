import pandas as pd

from scripts.creators import add_age_features, parse_staff, staff_date


def test_partial_birthdays_keep_their_precision():
    assert staff_date({"YearOfBirth": "1962"}, "Birth") == ("1962", 9, 1962)
    assert staff_date({"YearOfBirth": "1962", "MonthOfBirth": "November"}, "Birth") == (
        "1962-11",
        10,
        1962,
    )
    assert staff_date(
        {"YearOfBirth": "1962", "MonthOfBirth": "11", "DayOfBirth": "16"}, "Birth"
    ) == ("1962-11-16", 11, 1962)
    assert staff_date({"YearOfBirth": "1962 or 1963"}, "Birth") == (None, None, None)
    assert staff_date(
        {"YearOfBirth": "1962", "MonthOfBirth": "2", "DayOfBirth": "30"}, "Birth"
    ) == ("1962-02", 10, 1962)


def test_staff_template_provenance_and_gender_are_explicit():
    page = {
        "title": "Creator",
        "pageid": 42,
        "revisions": [
            {
                "revid": 123,
                "timestamp": "2026-10-21T00:00:00Z",
                "slots": {
                    "main": {
                        "*": """
{{DC Database:Staff Template | RealName=Creator | Gender=Non-binary | YearOfBirth=1960
| OfficialWebsite=[https://example.test/ Official site] }}"""
                    }
                },
            }
        ],
    }
    row = parse_staff(page)
    assert row["birth_date"] == "1960"
    assert row["gender"] == "non-binary"
    assert row["gender_source_value"] == "Non-binary"
    assert row["biography_revision_url"].endswith("oldid=123")
    assert row["official_website"] == "https://example.test/"
    assert parse_staff({"title": "Creator (New Earth)"}) == {
        "biography_match_status": "no_staff_template"
    }


def test_age_is_contemporaneous_and_posthumous_age_is_missing():
    links = pd.DataFrame(
        {
            "story_id": ["a", "a", "a", "b"],
            "creator_id": ["one", "two", "three", "one"],
            "publication_year_proxy": [2000, 2000, 2000, 1980],
        }
    )
    links["publication_year_proxy"] = pd.array(links.publication_year_proxy, dtype="Int64")
    creators = pd.DataFrame(
        {
            "creator_id": ["one", "two", "three"],
            "birth_year": [1960, 1900, None],
            "death_year": [2016, 1990, None],
        }
    )
    stories = pd.DataFrame(
        {"story_id": ["a", "b"], "discussion_date": ["2021-01-01", "2022-01-01"]}
    )
    result = add_age_features(links, creators, stories)
    assert result.loc[0, "age_at_publication_year_proxy"] == 40
    assert pd.isna(result.loc[0, "age_at_discussion_year_proxy"])
    assert result.loc[0, "age_at_discussion_status"] == "after_recorded_death_year"
    assert pd.isna(result.loc[1, "age_at_publication_year_proxy"])
    assert result.loc[1, "posthumous_publication_year"]
    assert pd.isna(result.loc[2, "age_at_publication_year_proxy"])
    assert pd.isna(result.loc[2, "posthumous_publication_year"])
    assert result.loc[3, "age_at_publication_year_proxy"] == 20


def test_same_death_year_and_nullable_publication_year_do_not_imply_age():
    links = pd.DataFrame(
        {
            "story_id": ["same", "missing"],
            "creator_id": ["one", "one"],
            "publication_year_proxy": pd.array([2016, None], dtype="Int64"),
        }
    )
    creators = pd.DataFrame({"creator_id": ["one"], "birth_year": [1962], "death_year": [2016]})
    stories = pd.DataFrame(
        {"story_id": ["same", "missing"], "discussion_date": ["2016-01-01", "2026-01-01"]}
    )
    result = add_age_features(links, creators, stories)
    assert result.loc[0, "age_at_publication_status"] == "same_death_year_order_unknown"
    assert pd.isna(result.loc[0, "age_at_publication_year_proxy"])
    assert pd.isna(result.loc[0, "posthumous_publication_year"])
    assert pd.isna(result.loc[0, "age_at_discussion_year_proxy"])
    assert result.loc[1, "age_at_publication_status"] == "unknown_date"
    assert pd.isna(result.loc[1, "age_at_publication_year_proxy"])
