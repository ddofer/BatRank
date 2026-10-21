"""Assemble creator, credit and award relations without making biography requests.

Names identify credit-name clusters until biography sources resolve identity. Official
award counts describe only matched events in the supplied extract, never all prizes.
"""

import hashlib
import json

import pandas as pd

from scripts.awards import ALIASES, ROLES as NARRATIVE_ROLES, normalize
from scripts.dataset import ROLES

PLACEHOLDERS = {
    normalize(v) for v in ["N/A", "Unknown", "None", "Various", "h1", "h2", "Uncredited", "?"]
}
CREDIT_KEYS = ["story_id", "creator_id", "role", "credit_scope"]
AWARD_KEYS = ["creator_id", "event_id"]
EVENT_COLUMNS = [
    "event_id",
    "award",
    "award_year",
    "category",
    "recipient_scope",
    "recipient_names",
    "winning_roles",
    "awarded_work",
    "source_url",
]


def alias_index(aliases=None):
    """An ambiguous curated alias must be fixed rather than silently picking a person."""
    result = {}
    for primary, variants in (ALIASES if aliases is None else aliases).items():
        for variant in [primary, *variants]:
            key = normalize(variant)
            if key in result and result[key] != primary:
                raise ValueError(
                    f"Ambiguous creator alias {variant!r}: {result[key]!r} / {primary!r}"
                )
            result[key] = primary
    return result


ALIASED = alias_index()


def _reviewed_aliases(aliases):
    lookup = {}
    for source, target in (aliases or {}).items():
        if (
            not isinstance(source, str)
            or not isinstance(target, str)
            or not normalize(source)
            or not normalize(target)
            or normalize(target) in PLACEHOLDERS
        ):
            raise ValueError("Creator aliases require nonempty names and a non-placeholder target")
        key = normalize(source)
        if key in lookup and normalize(lookup[key]) != normalize(target):
            raise ValueError(f"Conflicting normalized creator aliases: {source!r}")
        lookup[key] = target.strip()
    resolved = {}
    for key, target in lookup.items():
        visited = {key}
        while normalize(target) in lookup and normalize(lookup[normalize(target)]) != normalize(
            target
        ):
            next_key = normalize(target)
            if next_key in visited:
                raise ValueError(f"Cyclic creator aliases involving {target!r}")
            visited.add(next_key)
            target = lookup[next_key]
        resolved[key] = target
    return resolved


def _canonical_name(name, lookup):
    value = str(name).strip()
    value = lookup.get(normalize(value), value)
    return ALIASED.get(normalize(value), value)


def canonical_name(name, aliases=None):
    """Apply verified identity redirects, then the existing reviewed spelling aliases."""
    return _canonical_name(name, _reviewed_aliases(aliases))


def _name_id(name):
    return "cr_" + hashlib.sha256(normalize(name).encode()).hexdigest()[:12]


def creator_id(name, aliases=None):
    return _name_id(canonical_name(name, aliases))


def credit_names(value):
    if pd.isna(value):
        return []
    return [name.strip() for name in str(value).split("|") if name.strip()]


def checked_events(awards):
    events = {}
    for event in awards["events"]:
        if event["event_id"] in events and events[event["event_id"]] != event:
            raise ValueError(f"Conflicting award event ID: {event['event_id']}")
        events[event["event_id"]] = event
    return events


def _years(values):
    numeric = pd.to_numeric(values, errors="coerce")
    known = numeric.dropna()
    if not known.between(1800, 2100).all() or not known.eq(known.round()).all():
        raise ValueError("Contributing publication/cover years must be whole, plausible years")
    return numeric


def _clock(refs):
    actual = _years(refs.publication_year)
    cover = _years(refs.cover_year)
    if actual.notna().all():
        years, basis = actual, "actual_publication_year"
    elif cover.notna().all():
        years, basis = cover, "cover_year_proxy"
    else:
        years, basis = pd.Series(dtype=float), "unknown"
    return {
        "publication_year_proxy": int(years.min()) if len(years) else None,
        "publication_year_end_proxy": int(years.max()) if len(years) else None,
        "year_basis": basis,
        "actual_publication_year_reference_count": int(actual.notna().sum()),
        "cover_year_reference_count": int(cover.notna().sum()),
    }


def build_tables(stories, issues, awards, aliases=None):
    """Return creators, story_creators, creator_awards and a serializable audit dict.

    Creator clocks use only the references contributing that exact role and scope.
    Duplicate canonical references count once; source spellings remain in variants.
    """
    if not stories.story_id.is_unique:
        raise ValueError("Stories must have unique story_id values")
    if not set(issues.story_id) <= set(stories.story_id):
        raise ValueError("Issue references contain unknown story IDs")
    if issues.duplicated(["story_id", "requested_title"]).any():
        raise ValueError("Issue references must have unique story/requested-title keys")
    events = checked_events(awards)
    alias_lookup = _reviewed_aliases(aliases)
    scopes = {
        "whole_issue": {role: role for role in ROLES},
        "selected_narrative": {role: f"narrative_{role}" for role in NARRATIVE_ROLES},
    }
    rows, excluded = [], []
    for scope, columns in scopes.items():
        for role, column in columns.items():
            if column not in issues:
                continue
            for issue in issues.loc[issues[column].notna()].itertuples():
                for name in credit_names(getattr(issue, column)):
                    if not normalize(name) or normalize(name) in PLACEHOLDERS:
                        excluded.append({"value": name, "role": role, "credit_scope": scope})
                        continue
                    issue_id = getattr(issue, "issue_id", None)
                    wiki_title = getattr(issue, "wiki_title", None)
                    reference = (
                        f"wiki:{int(issue_id)}"
                        if pd.notna(issue_id)
                        else f"title:{wiki_title}"
                        if pd.notna(wiki_title)
                        else f"requested:{issue.requested_title}"
                    )
                    rows.append(
                        {
                            "story_id": issue.story_id,
                            "creator_id": _name_id(_canonical_name(name, alias_lookup)),
                            "role": role,
                            "credit_scope": scope,
                            "name": _canonical_name(name, alias_lookup),
                            "source_name": name,
                            "reference": reference,
                            "issue_title": wiki_title
                            if pd.notna(wiki_title)
                            else issue.requested_title,
                            "publication_year": getattr(issue, "publication_year", None),
                            "cover_year": getattr(issue, "cover_year", None),
                        }
                    )
    if not rows:
        raise ValueError("No usable creator credits found")
    expanded = pd.DataFrame(rows)
    creators = []
    for key, group in expanded.groupby("creator_id", sort=True):
        canonical = sorted(set(group.name), key=lambda value: (value.casefold(), value))
        creators.append(
            {
                "creator_id": key,
                "name": canonical[0],
                "credit_name_variants": "|".join(sorted(set(group.source_name))),
                "entity_type": "unresolved",
            }
        )
    creators = pd.DataFrame(creators)
    credits = []
    for keys, group in expanded.groupby(CREDIT_KEYS, sort=True):
        for field in ["publication_year", "cover_year"]:
            if group.groupby("reference")[field].nunique(dropna=True).gt(1).any():
                raise ValueError(f"Conflicting {field} on duplicate canonical reference: {keys}")
        refs = group.groupby("reference", as_index=False, sort=False).first()
        credits.append(
            {
                **dict(zip(CREDIT_KEYS, keys)),
                "reference_count": len(refs),
                "creator_name_variants": "|".join(sorted(set(group.source_name))),
                "contributing_issue_titles": "|".join(sorted(set(refs.issue_title))),
                **_clock(refs),
            }
        )
    credits = pd.DataFrame(credits)
    for field in ["publication_year_proxy", "publication_year_end_proxy"]:
        credits[field] = pd.array(credits[field], dtype="Int64")
    creator_ids = set(creators.creator_id)
    links, unmatched_recipients = [], set()
    for event in events.values():
        if event["recipient_scope"] not in {"personal", "honor"}:
            continue
        for name in event["recipient_names"]:
            key = _name_id(_canonical_name(name, alias_lookup))
            if key not in creator_ids:
                unmatched_recipients.add(name)
                continue
            links.append(
                {
                    "creator_id": key,
                    "event_id": event["event_id"],
                    "award": event["award"],
                    "award_year": int(event["award_year"]),
                    "category": event["category"],
                    "recipient_scope": event["recipient_scope"],
                    "recipient_name": name,
                }
            )
    award_columns = [
        *AWARD_KEYS,
        "award",
        "award_year",
        "category",
        "recipient_scope",
        "recipient_name",
    ]
    creator_awards = pd.DataFrame(links, columns=award_columns)
    if not creator_awards.empty:
        creator_awards = creator_awards.groupby(AWARD_KEYS, as_index=False, sort=True).agg(
            {
                **{
                    column: "first"
                    for column in ["award", "award_year", "category", "recipient_scope"]
                },
                "recipient_name": lambda values: "|".join(sorted(set(values))),
            }
        )
    for name, system, scope in [
        ("eisner_personal_win_count_observed", "Eisner", "personal"),
        ("kirby_personal_win_count_observed", "Kirby", "personal"),
        ("hall_of_fame_event_count_observed", None, "honor"),
    ]:
        subset = creator_awards.loc[creator_awards.recipient_scope.eq(scope)]
        if system:
            subset = subset.loc[subset.award.eq(system)]
        if scope == "honor":
            subset = subset.loc[subset.category.eq("Hall of Fame")]
        counts = subset.groupby("creator_id").event_id.nunique()
        creators[name] = creators.creator_id.map(counts).fillna(0).astype(int)
    ids = creator_awards.groupby("creator_id").event_id.agg(
        lambda values: "|".join(sorted(set(values)))
    )
    creators["award_event_ids_observed"] = creators.creator_id.map(ids).fillna("")
    creators["award_match_status"] = creators.award_event_ids_observed.map(
        lambda value: (
            "matched_personal_or_honor_events" if value else "no_matched_personal_or_honor_event"
        )
    )
    years = awards.get("award_years", sorted({e["award_year"] for e in events.values()}))
    creators["award_universe_year_start"] = min(years) if years else None
    creators["award_universe_year_end"] = max(years) if years else None
    creators["award_coverage_scope"] = "supplied_official_eisner_kirby_matched_events"
    assert creators.creator_id.is_unique
    assert not credits.duplicated(CREDIT_KEYS).any()
    assert not creator_awards.duplicated(AWARD_KEYS).any()
    assert set(creator_awards.creator_id) <= creator_ids
    assert set(creator_awards.event_id) <= set(events)
    assert (
        not credits.loc[credits.credit_scope.eq("selected_narrative"), "role"]
        .isin(["cover_artists", "executive_editors"])
        .any()
    )
    validation = {
        "creators": len(creators),
        "story_creator_rows": len(credits),
        "creator_award_rows": len(creator_awards),
        "stories_with_creator_links": credits.story_id.nunique(),
        "excluded_placeholder_occurrences": len(excluded),
        "excluded_placeholder_values": pd.Series([row["value"] for row in excluded], dtype=str)
        .value_counts()
        .to_dict(),
        "merged_credit_name_clusters": creators.loc[
            creators.credit_name_variants.str.contains("|", regex=False),
            ["creator_id", "name", "credit_name_variants"],
        ].to_dict("records"),
        "unmatched_supplied_award_recipient_names": sorted(unmatched_recipients),
        "year_basis_counts": credits.year_basis.value_counts().to_dict(),
        "coverage_note": "Counts are distinct matched personal/honor source events in the supplied official Eisner/Kirby extract. Zero means no matched event in this universe, not no awards. Work prizes are excluded from creator totals. Recipient matching coverage is limited to the creator index used to parse the supplied events; no extra recipients are inferred from winning works.",
        "identity_note": "Stable IDs identify normalized credit-name clusters with reviewed aliases; unverified homonyms and studios are not automatically classified as people.",
    }
    # Keep the audit safe for JSON writers, including pandas-derived integer values.
    validation = json.loads(json.dumps(validation, default=lambda value: int(value)))
    return creators, credits, creator_awards, validation


def extend_award_audit(existing, awards, creator_awards):
    """Refresh existing events and append linked personal/honor events; preserve work rows."""
    events = checked_events(awards)
    required = set(existing.event_id) | set(creator_awards.event_id)
    missing = required - set(events)
    if missing:
        raise ValueError(f"Award audit contains unknown event IDs: {sorted(missing)}")
    rows = []
    for event_id in sorted(required):
        event = events[event_id]
        rows.append(
            {
                **{key: event.get(key, "") for key in EVENT_COLUMNS},
                "recipient_names": "|".join(event["recipient_names"]),
                "winning_roles": "|".join(event["winning_roles"]),
            }
        )
    return pd.DataFrame(rows, columns=EVENT_COLUMNS)
