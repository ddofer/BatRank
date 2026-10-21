"""Build creator features and role links from cached, revision-attributed staff records."""

import argparse
import calendar
import json
import re
from datetime import date
from urllib.parse import quote

import mwparserfromhell
import pandas as pd

from scripts import awards
from scripts.creator_tables import build_tables, extend_award_audit
from scripts.dataset import OUT, ROLES, ROOT, Fetcher, clean, wiki_pages

MISSING = {"", "n/a", "unknown", "none", "various", "not applicable", "unspecified"}


def staff_fields(page):
    text = page.get("revisions", [{}])[0].get("slots", {}).get("main", {}).get("*", "")
    if "Staff Template" not in text:
        return {}
    template = next(
        (
            t
            for t in mwparserfromhell.parse(text).filter_templates()
            if str(t.name).strip().casefold() == "dc database:staff template"
        ),
        None,
    )
    if template is None:
        return {}
    fields = {str(p.name).strip(): clean(p.value) for p in template.params}
    if template.has("OfficialWebsite"):
        urls = re.findall(r"https?://[^\s\]<>|]+", str(template.get("OfficialWebsite").value))
        fields["OfficialWebsite"] = "|".join(dict.fromkeys(urls))
    return fields


def staff_date(fields, event):
    """Keep year/month precision; never turn an absent birthday into January 1."""
    raw = fields.get(f"YearOf{event}", "")
    if not re.fullmatch(r"\d{4}", raw):
        return None, None, None
    year = int(raw)
    if not 1 <= year <= 2030:
        raise ValueError(f"Implausible staff {event.lower()} year: {year}")
    month_text = fields.get(f"MonthOf{event}", "").casefold()
    months = {name.casefold(): n for n, name in enumerate(calendar.month_name) if name}
    months.update({name.casefold(): n for n, name in enumerate(calendar.month_abbr) if name})
    month = int(month_text) if month_text.isdigit() else months.get(month_text)
    if not month or not 1 <= month <= 12:
        return str(year), 9, year
    value = f"{year:04}-{month:02}"
    day = fields.get(f"DayOf{event}", "")
    if not day.isdigit():
        return value, 10, year
    try:
        exact = date(year, month, int(day))
    except ValueError:
        return value, 10, year
    return exact.isoformat(), 11, year


def parse_staff(page):
    fields = staff_fields(page)
    if not fields:
        return {"biography_match_status": "no_staff_template"}
    revision = page["revisions"][0]
    url = "https://dc.fandom.com/wiki/" + quote(page["title"].replace(" ", "_"))
    gender = fields.get("Gender", "")
    row = dict(
        biography_match_status="exact_or_redirect_staff_template",
        biography_name=fields.get("RealName") or None,
        biography_page_id=page["pageid"],
        biography_source_url=url,
        biography_revision_id=revision["revid"],
        biography_revision_timestamp=revision["timestamp"],
        biography_revision_url=f"https://dc.fandom.com/wiki/?oldid={revision['revid']}",
        gender_source_value=gender or None,
        gender=gender.casefold() if gender.casefold() not in MISSING else None,
        gender_scope="wiki_staff_assertion_at_snapshot",
        birth_year_source_value=fields.get("YearOfBirth") or None,
        death_year_source_value=fields.get("YearOfDeath") or None,
        birth_country=fields.get("CountryOfBirth") or None,
        birth_state=fields.get("StateOfBirth") or None,
        birth_city=fields.get("CityOfBirth") or None,
        staff_titles=fields.get("Titles") or None,
        staff_employers=fields.get("Employers") or None,
        staff_pseudonyms=fields.get("Pseudonyms") or None,
        first_dc_credit_source_label=fields.get("First") or None,
        official_website=fields.get("OfficialWebsite") or None,
    )
    for event in ["Birth", "Death"]:
        (
            row[f"{event.lower()}_date"],
            row[f"{event.lower()}_date_precision"],
            row[f"{event.lower()}_year"],
        ) = staff_date(fields, event)
    return row


def add_age_features(links, creators, stories):
    joined = links.merge(
        creators[["creator_id", "birth_year", "death_year"]],
        on="creator_id",
        validate="many_to_one",
    ).merge(stories[["story_id", "discussion_date"]], on="story_id", validate="many_to_one")
    discussion = pd.to_datetime(joined.discussion_date).dt.year
    for context, years in [
        ("publication", joined.publication_year_proxy),
        ("discussion", discussion),
    ]:
        age = years - joined.birth_year
        same_death_year = (
            years.eq(joined.death_year) & years.notna() & joined.death_year.notna()
        ).fillna(False)
        posthumous = (
            years.gt(joined.death_year)
            .astype("boolean")
            .where(years.notna() & joined.death_year.notna() & ~same_death_year)
        )
        valid = (
            age.between(0, 110) & ~posthumous.fillna(False).astype(bool) & ~same_death_year
        ).fillna(False)
        links[f"age_at_{context}_year_proxy"] = age.where(valid)
        links[f"posthumous_{context}_year"] = posthumous
        links[f"age_at_{context}_status"] = [
            "year_difference_proxy"
            if ok
            else "same_death_year_order_unknown"
            if same_year
            else "after_recorded_death_year"
            if pd.notna(dead) and bool(dead)
            else "before_birth_year"
            if pd.notna(a) and a < 0
            else "implausible_age"
            if pd.notna(a) and a > 110
            else "unknown_date"
            for ok, same_year, dead, a in zip(valid, same_death_year, posthumous, age)
        ]
    return links


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    stories = pd.read_csv(OUT / "stories.csv")
    issues = pd.read_csv(OUT / "issues.csv")
    people = set().union(*(awards.names(v) for role in ROLES for v in stories[role]))
    people -= {"N/A", "Unknown", "None", "Various", "h1", "h2"}
    people.update(v for k, vs in awards.ALIASES.items() if k in people for v in vs)
    pages = wiki_pages(Fetcher(args.offline), sorted(people))
    # Staff redirects resolve source credit clusters; some targets are companies, not people.
    staff = {name: parse_staff(page) for name, page in pages.items()}
    aliases = {
        name: pages[name]["title"]
        for name in sorted(staff)
        if staff[name]["biography_match_status"] != "no_staff_template"
        and name != pages[name]["title"]
    }
    (ROOT / "references/creator_aliases.json").write_text(
        json.dumps(aliases, indent=2, ensure_ascii=False) + "\n"
    )
    snapshot = json.loads((ROOT / "data/external/awards.json").read_text())
    # Re-index the same official winners for all eight credited roles, including cover-only artists.
    from scripts.creator_tables import canonical_name

    entity_types = json.loads((ROOT / "references/creator_entity_types.json").read_text())
    index = {
        awards.normalize(name): canonical_name(name, aliases)
        for name in sorted(people)
        if aliases.get(name, name) not in entity_types
    }
    events = []
    for decade, url in awards.SOURCES.items():
        parsed, _ = awards.parse_winners((awards.RAW / f"{decade}.html").read_text(), url, index)
        events.extend(parsed)
    snapshot["events"] = events
    creators, links, creator_awards, validation = build_tables(
        stories, issues, snapshot, aliases=aliases
    )
    biographies = []
    for creator in creators.itertuples():
        candidates = [
            staff[n]
            for n in creator.credit_name_variants.split("|")
            if n in staff and staff[n]["biography_match_status"] != "no_staff_template"
        ]
        ids = {r["biography_page_id"] for r in candidates}
        if len(ids) > 1:
            raise ValueError(f"Conflicting staff identities: {creator.name}: {ids}")
        biographies.append(
            {
                "creator_id": creator.creator_id,
                **(
                    candidates[0] if candidates else {"biography_match_status": "no_staff_template"}
                ),
            }
        )
    creators = creators.merge(pd.DataFrame(biographies), on="creator_id", validate="one_to_one")
    creators.loc[creators.biography_page_id.notna(), "entity_type"] = "staff_record_unclassified"
    for field in ["entity_type", "source_url", "note"]:
        values = {page: row[field] for page, row in entity_types.items()}
        mapped = creators.biography_source_url.map(
            {
                "https://dc.fandom.com/wiki/" + quote(page.replace(" ", "_")): value
                for page, value in values.items()
            }
        )
        if field == "entity_type":
            creators[field] = mapped.fillna(creators[field])
        else:
            creators["entity_type_" + field] = mapped
    nonpeople = creators.entity_type.isin(["organization", "collective"])
    creators.loc[
        nonpeople,
        [
            "birth_date",
            "birth_date_precision",
            "birth_year",
            "death_date",
            "death_date_precision",
            "death_year",
            "gender",
        ],
    ] = None
    creators.loc[nonpeople, "biography_match_status"] = "nonperson_staff_record"
    personal_counts = [
        "eisner_personal_win_count_observed",
        "kirby_personal_win_count_observed",
        "hall_of_fame_event_count_observed",
    ]
    creators.loc[nonpeople, personal_counts] = None
    creators.loc[nonpeople, "award_match_status"] = "not_a_personal_award_entity"
    identities = json.loads((ROOT / "references/creator_matches.json").read_text())["matches"]
    identity_by_name = {canonical_name(row["creator_name"], aliases): row for row in identities}
    for field in ["wikidata_id", "source_url", "match_proof"]:
        creators["wikidata_" + field.removeprefix("wikidata_")] = creators.name.map(
            {name: row[field] for name, row in identity_by_name.items()}
        )
    links = add_age_features(links, creators, stories)
    assert not creator_awards.creator_id.isin(creators.loc[nonpeople, "creator_id"]).any()
    assert (
        links.loc[
            links.creator_id.isin(creators.loc[nonpeople, "creator_id"]),
            ["age_at_publication_year_proxy", "age_at_discussion_year_proxy"],
        ]
        .isna()
        .all()
        .all()
    )
    used = pd.read_csv(ROOT / "references/award_events.csv")
    extend_award_audit(used, snapshot, creator_awards).to_csv(
        ROOT / "references/award_events.csv", index=False
    )
    for name, table in [
        ("creators", creators),
        ("story_creators", links),
        ("creator_awards", creator_awards),
    ]:
        table.to_csv(OUT / f"{name}.csv", index=False)
    validation["biography_coverage"] = {
        column: int(creators[column].notna().sum())
        for column in ["biography_page_id", "birth_year", "death_year", "gender", "birth_country"]
    }
    validation["age_coverage"] = {
        column: int(links[column].notna().sum())
        for column in ["age_at_publication_year_proxy", "age_at_discussion_year_proxy"]
    }
    validation["age_status_counts"] = links.age_at_publication_status.value_counts().to_dict()
    validation["gender_source_values"] = creators.gender.value_counts().to_dict()
    validation["source_note"] = (
        "DC Database staff-template assertions, with exact revision provenance. Gender is not inferred or necessarily self-described; it is not a historical-at-publication measurement. Staff records can include collectives. Year differences are age proxies; posthumous dates receive no age. Official award events are re-indexed for all eight source-credit roles, never treating work wins as personal prizes."
    )
    (ROOT / "reports/creators_validation.json").write_text(json.dumps(validation, indent=2) + "\n")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
