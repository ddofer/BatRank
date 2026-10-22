# Data dictionary

The canonical processed snapshot contains **740 ranked entries × 162 columns**. The upload splits it into **21 columns in `stories.csv`** (rank and title first) and **142 in `story_features.csv`**, with only `story_id` repeated. A one-to-one join reconstructs every original field. `issues.csv` contains **2,434 story–reference associations × 78 columns**. One ranked entry can be an arc, an original graphic novel, a backup, an anthology, or several stories read together.

All files are UTF-8 CSV without a saved dataframe index. Empty fields mean unavailable or inapplicable; booleans use `True`/`False`. Nullable counts and years can serialize as decimals. Multi-value names, wiki targets and event IDs use `|`; GCD type/URL lists and publisher credit lists use `; `. `work_award_matches` is a JSON array inside a quoted CSV cell. Sets are deduplicated; matching names does not resolve every alias or prove who physically drew an historically disputed credit.

Join the tables on `story_id`; `(story_id, requested_title)` uniquely identifies an issue-table row. The same issue can occur in several readings. Deduplicate `issue_id` when counting global wiki issues, and keep shared issues/episode companions together during validation. An exploded join is not a larger sample of independent ranked stories.

## Ranked entries: identity, bibliography and original metadata

These fields occur in the joined story tables (`stories.csv` and `story_features.csv`).

| Columns | Definition |
|---|---|
| `story_id` | First 12 hexadecimal characters of SHA-256 of `source_label`; independent of rank. Editing the original label changes the ID. |
| `source_label`, `title`, `issues_raw`, `source_year` | Original label without its number, minimally parsed title, source issue text and source year. Only the top-five HTML cards supply `source_year`; it is not filled from another source. |
| `source_rank`, `rank`, `rank_label_disagrees` | Printed number, unique consecutive page position starting at 1, and whether they disagree. The source repeats some printed numbers; `rank` is the analysis target. |
| `rank_percentile` | `(rank − 1) / 739`: 0 is best, 1 is worst. A target-derived value, not an input feature. |
| `episode_url`, `discussion_date`, `discussion_date_source` | Episode link and date proxy from its URL, otherwise an exact SoundCloud URL match to public RSS. Provenance records which method supplied the date. Not independently verified audio-release timing. |
| `issue_list_note`, `issue_list_complete` | Reviewed correction/reading-list explanation and whether the listed references represent the resolved whole reading. Unspecified event scope and partial/unresolved lists remain incomplete. |
| `issue_reference_count`, `matched_issue_count`, `metadata_coverage` | Number of candidate references, distinct matched wiki issue IDs, and matched IDs divided by references. Coverage 1 does not establish complete credits or known event scope. |
| `metadata_complete`, `issue_count` | All references match and the reading list is complete; issue count is supplied only under that condition. Digital chapters and collected manga volumes are still references, not equivalent-length units. |
| `cover_year_start`, `cover_year_end`, `publication_year_start` | Earliest/latest known cover years and earliest explicitly recorded publication year among matched issues. A partial set of dates may miss the true start/end. Publication year is not inferred from a cover year. |
| `page_count` | Sum of wiki whole-issue page counts only when the list is complete and every issue supplies a numeric count. Almost entirely unavailable; see the separate GCD narrative counts below. |
| `credit_scope` | `whole_issue_including_backups`: the original creator columns include unrelated substories. They are retained alongside, rather than replaced by, narrative attribution. |
| `synopsis_opening`, `synopsis_source_url`, `synopsis_scope` | Up to 1,200 cleaned characters from the first available issue's **first** story opening; scope is `opening_of_first_available_issue_first_story`. It is neither a whole-arc summary nor necessarily the selected backup. NLP measures the wiki summarizer's prose. |
| `medium`, `format_hint` | `comic`, `webcomic`, `manga` or `unknown`; `original_graphic_novel` only when the source explicitly says OGN, otherwise `unspecified`. Animation-themed comic adaptations remain comics. |
| `cover_url` | Source cover link for the top-five cards, otherwise a wiki Special:Redirect/file link from an available issue. A link is not image redistribution permission. |
| `creator_watch_names`, `creator_watch_sources`, `creator_watch_count`, `creator_watch_status` | Exact matches against the small cited creator-event list, including whole-issue backup, editorial and executive-editor credits. Names and source URLs correspond in list order. Status is `documented_event_in_issue_credits` or `unreviewed`; zero is not a reviewed negative or misconduct score. Allegations and convictions remain distinct in the source list. |
| `snapshot_date`, `ranking_source_url` | Cached rankings HTML date and source URL. Metadata/ratings can have different retrieval and revision dates. |

## Issue/reference keys and source records

These fields occur in `issues.csv`.

| Columns | Definition |
|---|---|
| `story_id`, `requested_title` | Ranked-entry foreign key and expanded reference before curated lookup aliases. Reading-list corrections are documented at story level. |
| `lookup_title`, `lookup_aliased` | Title queried through the wiki API and whether a reviewed alias was applied. Volume 1 is the parser default when no volume is stated; unresolved ambiguity remains visible. |
| `wiki_title`, `issue_id`, `match_status` | API-resolved page title/ID and `matched_comic_issue` or `unmatched`. A real Comic Template is required; character, series and disambiguation pages do not qualify. |
| `metadata_url`, `revision_id`, `revision_timestamp` | Wiki source and revision provenance. An exact revision is accessible as `https://dc.fandom.com/wiki/?oldid=REVISION_ID`. |
| `cover_year`, `cover_month`, `publication_year`, `publication_month`, `publication_day` | Cleaned date components, retaining incomplete dates. Publication components come from `Pubyear`, `Pubmonth`, `Day`; no fabricated complete date. Cover month may be numeric or named. |
| `page_count`, `issue_story_titles`, `synopsis_opening`, `cover_url` | Wiki whole-issue pages; all named indexed substories joined by `\|`; first-story opening excerpt; issue cover link. These retain the original whole-issue/first-story scopes. |

## Credits, substory selection and cast

The eight original credit columns appear in both tables: `writers`, `pencilers`, `inkers`, `colorists`, `letterers`, `editors`, `cover_artists`, `executive_editors`. Issue rows collect all substories' credits; story rows take their sorted union over matched issues. Names and collective studio credits retain the source's distinctions.

The six attributed columns also appear in both tables: `narrative_writers`, `narrative_pencilers`, `narrative_inkers`, `narrative_colorists`, `narrative_letterers`, `narrative_editors`. They use only selected indexed narratives. Story rows union available attributed names; an unresolved reference can leave an incomplete union. Check coverage before treating these as the complete crew. Placeholder credits such as N/A/unknown are excluded. Cover and executive-editor roles are not silently assigned to narratives.

| Table / columns | Definition |
|---|---|
| issues: `indexed_substory_count`, `selected_substory_indexes`, `selected_substory_titles` | Number of nonempty indexed story-title/credit/appearance/synopsis slots, selected slot numbers, and their titles. The count is an indexing measure; it can include material explicitly excluded by a reviewed override. |
| issues: `substory_match_status` | `single_substory`, `explicit_title_match`, `reviewed_override`, `ambiguous_whole_issue`, or `no_indexed_substories`. Ambiguous multi-story issues are not assigned guessed narrative credits. |
| issues: `substory_match_note`, `substory_match_source_url` | Reason and source for a reviewed override; automatic title matches do not fabricate a manual-review note. |
| issues: `appearance_scope`, `appearance_indexed_sections` | `selected_narrative` or `whole_issue_unresolved`; number of selected/fallback indexed appearance sections containing at least one non-location linked entity, in any appearance mode. A locations-only section does not establish cast coverage. |
| both: `featured_entity_ids`, `supporting_entity_ids`, `antagonists_entity_ids`, `other_entity_ids`, `locations_entity_ids` | Deduplicated ordinary-appearance wiki targets from the respective source headings. IDs are page-title strings, not numeric person IDs or redirect-resolved entities. Groups/institutions can occur. Role labels are not narrator/viewpoint measurements. Story rows union references. |
| issues: `featured_entity_names`, `supporting_entity_names`, `antagonists_entity_names`, `other_entity_names`, `locations_entity_names` | Source display names, positionally aligned with the corresponding sorted ID list. Display names can vary between issues. |
| both: `mentioned_entity_ids`, `flashback_entity_ids`, `cameo_entity_ids`, `depiction_entity_ids`, `behind_scenes_entity_ids` | Non-location entities carrying those qualifiers, across role headings. Annotation links are excluded; parent qualifiers can be inherited by nested list entries. An explicitly mixed present/flashback appearance can occur in both ordinary and flashback sets. |
| both: `character_universe_qualifiers` | Distinct trailing parenthetical qualifiers on ordinary non-location targets, e.g. New Earth/Earth-One. Extracted labels, not independently verified continuity assignments. |
| issues: `ordinary_cast_entity_count` | Distinct ordinary non-location entities across cast roles. Missing when no indexed non-location appearance section was recovered; zero can mean only qualified appearances were indexed. |
| stories: `featured_entity_count`, `supporting_entity_count`, `antagonists_entity_count`, `other_entity_count`, `locations_entity_count` | Sizes of the corresponding unioned ID sets. Missing when no cast-bearing appearance section exists anywhere in the listed references. These are indexed entities, not a count of people drawn on panel. |
| stories: `cast_issue_coverage`, `cast_scope` | Fraction of listed references with a cast-bearing indexed appearance section; `selected_narratives` only if every reference's attribution resolved, otherwise `includes_whole_issue_unresolved`. Scope and coverage are separate checks. |
| stories: `substory_attribution_coverage`, `multi_substory_issue_count` | Fraction of references with selected narratives and number with more than one indexed substory. Full attribution does not establish a complete event reading list or complete credits in every craft. |

For strict character comparisons, require `cast_scope == 'selected_narratives'` and `cast_issue_coverage == 1`. Coverage is reference-level: it does not guarantee that every selected substory in a multi-story reference has its own cast list. Missing lists are not evidence that a character never appears. The notebooks combine selected base names across continuity qualifiers for a labeled plot only; the CSV preserves the qualified targets.

## Team continuity, age and collection links

Team features occur in `story_features.csv`. References follow their listed reading order and receive equal weight; they are not weighted by narrative pages.

| Columns | Definition |
|---|---|
| `narrative_credit_issue_coverage` | References with both nonempty attributed writer and penciler sets / all listed references. It does not require every colorist, letterer or editor to be known. |
| `narrative_team_count`, `narrative_dominant_team_share` | Number of distinct `(writer set, penciler set)` teams among known-team references; largest team's reference count divided by known-team reference count. Missing if no team is known. |
| `narrative_team_switch_count`, `narrative_team_comparable_transitions` | Different-team transitions and number of adjacent reference pairs with both teams known. Unknown references are not bridged. Switch count is missing when no pair is comparable; a known unchanged pair contributes zero. |
| `narrative_writer_artist_overlap_share` | For each selected narrative with writers and pencilers, whether their sets intersect; average within each issue, then average over known-team references with a measured overlap. Writing one anthology story and drawing another does not create self-authorship. |
| `narrative_self_inking_share`, `narrative_inking_issue_coverage` | For each selected narrative with pencils and inks, fraction of its pencilers also credited as inkers; average within each issue, then over references with that measurement. Coverage is measured references / all references. Not a fraction of pages self-inked. |
| `publication_age_year_proxy`, `cover_age_year_proxy` | Discussion calendar year minus earliest publication/cover year, respectively, only when every listed reference supplies that date type. No month/day adjustment. An incomplete reading list can still understate the reading's age/span. |
| `collection_count`, `collection_scope` | Number of distinct recorded collection targets and `issue_notes_may_reference_other_substories` when any were recovered. No links means none recovered, not no reprints. |

`collection_titles` and `collection_urls` appear in both tables and align positionally. They come from collection templates/links in issue Notes, not recommendations or sales data. Story rows union reference links. Issue `collection_link_scope` has the same issue-notes warning as story `collection_scope`. Current links are not an as-of-discussion bibliography.

## External ratings

In the upload, Goodreads fields occur in `story_features.csv`; RoundUp scores/counts occur in `story_features.csv` and `issues.csv`.

| Columns | Definition |
|---|---|
| `goodreads_book_id`, `goodreads_url`, `goodreads_title`, `goodreads_author` | Reviewed edition ID/link and public title/first listed author. Matching uses explicit mappings and creator cross-checks, not an automatically accepted fuzzy-title match. |
| `goodreads_rating`, `goodreads_rating_count` | Public shelf or book-page aggregate on the native 1–5 scale and rating count. Goodreads can pool editions at work level; a book URL does not guarantee edition-specific ratings or identical coloring/supplements. |
| `goodreads_match_scope`, `goodreads_match_note` | `same_story` for the same named narrative, `broader_collection` for extra stories, `subset` for a partial/unverified whole-reading equivalence; accompanying scope explanation. Not a numeric confidence score. |
| `goodreads_shelf_url`, `goodreads_retrieved_at` | Shelf URL when sampled from a shelf (empty for book-page extraction, whose source is `goodreads_url`), and cached response timestamp in UTC. |
| `roundup_user_rating`, `roundup_critic_rating` | Native issue scores on 0–10 scales; story values are **equal-weight means of scored references**, separately by audience. They can summarize partial lists; not weighted by review counts. |
| `roundup_user_count`, `roundup_critic_count` | Issue audience counts; story values sum available issue counts. These are issue-review observations, not distinct people, independent votes or confidence intervals. |
| stories: `roundup_user_min_count`, `roundup_critic_min_count` | Smallest count among that audience's scored references. It says nothing about unscored references. |
| stories: `roundup_user_coverage`, `roundup_critic_coverage` | Scored references / all candidate references. Zero means no matched score recovered, not a zero rating. |
| stories: `roundup_user_complete`, `roundup_critic_complete` | Every reference scored for that audience **and** `issue_list_complete` true. Separate from metadata/credit completeness. |
| stories: `roundup_scope` | Legacy heuristic: `whole_issue_proxy` for pre-1970 material or known backup/anthology/annual patterns, otherwise `listed_issues`. Retained for reproducibility; use the indexed narrative scope below for stricter matching. |
| both: `roundup_narrative_scope` | `all_indexed_narratives` when nonempty selected indexes include every indexed substory; `ranked_subset_of_issue` when fewer were selected; `unresolved_issue_scope` otherwise. Story scope takes unresolved if any reference is unresolved, otherwise subset if any is a subset. This is a content-scope audit, independent of whether any score exists. |
| issues: `roundup_url`, `roundup_catalogue_url`, `roundup_retrieved_at` | Public issue URL, actual series page supplying the aggregate, and cached response timestamp in UTC. |
| issues: `roundup_listed_creators`, `roundup_credit_check` | Catalogue names and `overlap`/`unavailable`: at least one normalized writer/artist agrees with wiki credits, or usable catalogue names are unavailable. Conflicts are excluded and reported, not quietly accepted. Overlap does not validate every credit. |

Strict notebook comparisons use Goodreads `same_story`, or RoundUp audience completeness **plus** `all_indexed_narratives`, then explicit count thresholds. Review-count screening uses the weakest issue; predictive vote controls use Goodreads total ratings or RoundUp mean issue-review observations (`roundup_*_count / issue_reference_count`). These controls, log transforms, availability flags and the derived switch rate live in analysis code, not extra canonical CSV columns. Current ratings support retrospective comparisons, not historical forecasts.

`references/goodreads_matches.csv` and `goodreads_matches_additions.csv` record curated book IDs and scope decisions. `references/roundup_series.json` and `roundup_series_additions.json` map verified wiki series/volumes to catalogue URLs, including Detective Comics’ resumed #934+ numbering in its 2016 catalogue. Numbered annuals and explicitly crosswalked named specials are supported; `roundup_issue_matches.json` records special issue tokens. Unresolved digital/print numbering and duplicate catalogue issue numbers remain excluded. No individual reviewer identities or review prose is exported.

## Creator and work awards

Award features occur in `stories.csv`. The reviewed universe is official Eisner **winners, 1988–2025**, plus predecessor Kirby winners **1985–1987**; no ceremony in 1990. Nominees and unreviewed award systems/years are excluded. `award_events.csv` resolves all exported event IDs. Detailed sources and assumptions are in `references/awards_sources.md`.

| Columns | Definition |
|---|---|
| `awards_coverage_status` | Explicit award-universe/year-span and curated-work-match warning. Zero means no matched record in that universe, not no prizes anywhere. |
| `awards_credit_scope`, `awards_creator_matching_status`, `awards_credited_creator_count` | `selected_narratives` when every reference is attributed and has writer/penciler credits, otherwise `whole_issue_credits_fallback`; `credited_names_reviewed` or `missing_credits`; distinct recorded interior/editor crew size used in matching. Cover-only and executive-editor contributors are excluded. |
| `awards_publication_year_basis`, `awards_prepublication_coverage`, `awards_prepublication_observed_years` | Actual publication year only when every reference supplies it, otherwise cover-year proxy/unknown; observed-since-1988 or not-started/unknown status; number of observed Eisner years strictly before that year, excluding 1990. |
| `creator_eisner_personal_wins_total`, `creator_kirby_personal_wins_total` | Distinct personal-category award events associated with recorded crew names in each award system. The winning book may be unrelated to Batman. A shared win is one event, even if several crew members share it. |
| `creator_eisner_personal_wins_pre_publication`, `creator_eisner_personal_wins_pre_discussion`, `creator_eisner_personal_wins_after_discussion_year` | Personal Eisner events strictly before publication/discussion year or strictly after discussion year. Same-year events are excluded from those respective clocks. Prepublication values are missing for publication in/before 1988 or unknown, rather than a clean negative history. |
| `creator_eisner_personal_award_holders_pre_publication` | Distinct matched crew members with at least one observed personal Eisner win strictly before publication; same eligibility rule. Useful with crew size. |
| `creator_eisner_hall_of_fame_total`, `creator_eisner_hall_of_fame_pre_publication` | Distinct matched inducted people, not annual craft events. The latter uses the strict prepublication clock/eligibility rule. Career/posthumous honors remain separate from personal craft wins. |
| `creator_award_names`, `creator_award_event_ids` | Matched crew names and referenced personal/honor events across Eisner and Kirby, including retrospective totals. ID order is not positional with the name set. |
| `writers_eisner_role_wins_pre_publication`, `pencilers_eisner_role_wins_pre_publication`, `inkers_eisner_role_wins_pre_publication`, `colorists_eisner_role_wins_pre_publication`, `letterers_eisner_role_wins_pre_publication` | Personal wins where the contributor is credited in that narrative/issue role and the winning category covers that craft. Same strict publication cutoff; missing before the observed award window. |
| `writers_eisner_role_wins_pre_discussion`, `pencilers_eisner_role_wins_pre_discussion`, `inkers_eisner_role_wins_pre_discussion`, `colorists_eisner_role_wins_pre_discussion`, `letterers_eisner_role_wins_pre_discussion` | Corresponding role/category intersections strictly before discussion year. Joint writer/artist or penciler/inker categories do not establish each recipient's individual winning duty. |
| `work_eisner_exact_work_wins`, `work_eisner_contained_story_wins`, `work_eisner_series_context_wins` | Curated wins for the ranked work itself, a story inside its anthology, or its eligible-year series context. None is interchangeable with a personal craft award. |
| `work_eisner_collected_edition_wins`, `work_eisner_edition_design_wins`, `work_eisner_archival_edition_wins` | Separate later collection, design and archival-edition recognition; totals can postdate the original work and podcast. |
| `work_eisner_exact_work_wins_pre_discussion`, `work_eisner_matched_wins_after_discussion_year` | Exact-work wins strictly before discussion year; all curated work-scope matches strictly after that year. |
| `work_awards_match_status`, `work_award_matches` | `verified_positive` or `not_exhaustively_reviewed`; JSON records containing `event_id`, `scope`, `note`. Zero curated matches is not a verified absence of awards. |

Totals are retrospective descriptors. A historical prediction must use the corresponding prior-year columns, retain eligibility/clock provenance, and account for era, observed window and crew size. Missing craft credits remain a separate limitation even within eligible award windows.

## GCD narrative measurements and DC publisher editions

This is a **purposive, small source sample**, not a representative length survey. GCD records came from indexed primary text after direct access was challenged; clipped fields remain missing. Story-level details are portable in `references/catalogue_narratives.csv`. GCD and publisher facts have separate provenance/licensing; see README.

| Table / columns | Definition |
|---|---|
| stories: `gcd_narrative_page_count`, `gcd_page_count_scope` | Sum of verified original-issue narratives only when every reference in the complete reading list is represented; otherwise missing. Scope is `complete_ranked_narratives` or `partial_or_reprint_sample`. Fractional pages are retained. |
| stories: `gcd_sampled_narrative_page_count`, `gcd_sampled_reference_count`, `gcd_matched_reference_count`, `gcd_reference_coverage` | Sum over all sampled narrative records including marked reprints; number of represented canonical references; number represented by original-issue records; original represented references / all listed references. A sampled sum is not a full-story length. |
| both: `gcd_story_types`, `gcd_source_urls` | Recorded narrative types, e.g. comic story/text story, and supporting catalogue URLs. Not inferred genre or writing quality. |
| issues: `gcd_narrative_page_count`, `gcd_narrative_titles`, `gcd_match_scope` | Sum of selected sampled narrative pages when all those records match the original issue, their titles, and `original_issue` or `same_story_reprint`. Reprints do not supply an original-issue page count. |
| issues: `gcd_physical_issue_page_count`, `gcd_on_sale_date` | Original issue's physical pages and recorded on-sale date, only for original-issue matches. Physical pages can include covers, advertising and other narratives. |
| stories: `publisher_source_url`, `publisher_edition_title`, `publisher_edition_on_sale_date`, `publisher_physical_page_count` | Official DC product link, exact edition title/date and physical publication pages. A translated/reprint edition date is not the original material's date; physical pages are not measured narrative length. |
| stories: `publisher_writers`, `publisher_artists`, `publisher_colorists`, `publisher_letterers`, `publisher_cover_artists` | Publisher edition-level credited names, retaining its artist terminology. Stored separately from wiki/narrative credits; an anthology/collection credit need not belong to the selected substory. |
| stories: `publisher_match_scope`, `publisher_match_note` | `ranked_edition`, `ranked_collection`, or `contains_ranked_story`, with the reviewed relationship. For example, a collection containing *Draining* does not make its entire page count the length of *Draining*. |

Preserve original labels, scope flags, correction notes, source URLs and revision/event IDs when sharing derivatives. Source lists and raw-file hashes are recorded in the snapshot manifest; validation coverage and unresolved cases are in the reports.

## Creator identity, biography and role relations

Three supplementary tables keep creator attributes separate from ranked entries: `creators.csv` has one credit-name cluster per `creator_id`; `story_creators.csv` links those clusters to specific roles and reading scopes; `creator_awards.csv` links them to observed personal/honor events. These are separate joins, not extra independent ranking observations.

### creators.csv

| Columns | Definition |
|---|---|
| `creator_id`, `name`, `credit_name_variants` | `cr_` plus 12 SHA-256 hexadecimal characters of the normalized canonical credit name; display name; observed original credit spellings joined by `\|`. Normalization handles punctuation, case and accents; reviewed aliases and exact staff-page redirects can merge clusters. IDs depend on that curation and are not universal person identifiers. No fuzzy-name match is accepted. |
| `entity_type`, `entity_type_source_url`, `entity_type_note` | `organization` for an explicitly reviewed studio/firm, `staff_record_unclassified` for another matched staff record, or `unresolved`. Exact staff records can describe collectives. Revision-linked curation in `references/creator_entity_types.json` establishes positive non-person cases; omission does not certify a human. |
| `biography_match_status`, `biography_name`, `biography_page_id` | Exact/redirect staff-template match status, source RealName label and staff page ID. Status is `exact_or_redirect_staff_template`, `nonperson_staff_record`, or `no_staff_template`. A RealName field is not independent proof of legal name or person identity. |
| `biography_source_url`, `biography_revision_id`, `biography_revision_timestamp`, `biography_revision_url` | Staff page, exact source revision ID/time, and permanent revision link. Biography data comes from that DC Wiki revision, not the Wikidata crosswalk. |
| `gender_source_value`, `gender`, `gender_scope` | Raw staff Gender field; lowercased non-placeholder value; `wiki_staff_assertion_at_snapshot`. This is the wiki's current assertion, not inferred from a name, independently confirmed self-description, or historical gender at publication. Interpreted gender is suppressed for reviewed non-people. |
| `birth_year_source_value`, `death_year_source_value` | Original cleaned year fields, retained even when ambiguous/uninterpretable or when a studio's field represents a founding year. Heroic Age's source value 1992 is not exported as a person's birth year. |
| `birth_date`, `birth_date_precision`, `birth_year`, `death_date`, `death_date_precision`, `death_year` | Parsed dates with explicit precision: 9 = year (`YYYY`), 10 = month (`YYYY-MM`), 11 = day (`YYYY-MM-DD`). Partial dates are not padded with January 1. Ambiguous years remain missing; invalid days do not become invented birthdays. All interpreted birth/death fields are suppressed for reviewed organizations. |
| `birth_country`, `birth_state`, `birth_city` | Cleaned source place fields, not standardized nationality/citizenship or residence. For a studio, these can describe its location rather than a person's birthplace; retain entity type and source context. |
| `staff_titles`, `staff_employers`, `staff_pseudonyms`, `first_dc_credit_source_label`, `official_website` | Career-level staff assertions, first-credit label and extracted official-site links. They are not dated employment histories or credits on every ranked story. Source list punctuation can vary; website links use `\|` when multiple links exist. Pseudonym text alone does not create an identity merge. |
| `wikidata_id`, `wikidata_source_url`, `wikidata_match_proof` | Small explicitly reviewed identity crosswalk, with record URL and matching evidence. Missing IDs are not guessed. The crosswalk does not supply or validate the exported demographic values. |
| `eisner_personal_win_count_observed`, `kirby_personal_win_count_observed`, `hall_of_fame_event_count_observed` | Distinct linked personal events in each system, and distinct Hall of Fame events across the supplied systems. These are retrospective observed counts, not awards earned before every credited work. A person with honors in different systems can have multiple Hall of Fame events. |
| `award_event_ids_observed`, `award_match_status`, `award_coverage_scope`, `award_universe_year_start`, `award_universe_year_end` | `\|`-joined linked event IDs; matched/no-matched-personal-or-honor status; scope of the supplied official Eisner/Kirby recipient extract; its observed endpoints, 1985–2025. Endpoints do not imply an award in every year or exhaustive award-system coverage. Zero means no matched event in this universe; reviewed organizations instead have missing personal-award counts and `not_a_personal_award_entity` status. |

`references/creator_aliases.json` records exact staff redirects; `references/creator_matches.json` records reviewed external IDs. A redirect can connect a credit label to a firm: *Allen Jamison* redirects to the *Jamison* company page. This is retained as a source credit-name cluster, with the non-person warning; it does not equate a founder's biography with the company.

### story_creators.csv

The unique key is **`(story_id, creator_id, role, credit_scope)`**. `story_id` and `creator_id` reference the corresponding tables.

| Columns | Definition |
|---|---|
| `story_id`, `creator_id`, `role`, `credit_scope` | Reading, credit-name cluster, source role and `whole_issue` or `selected_narrative` attribution. Whole-issue rows cover all eight original roles; narrative rows cover the six attributed interior/editor roles. The two scopes overlap and must not be added as separate contributors. |
| `reference_count`, `creator_name_variants`, `contributing_issue_titles` | Distinct canonical references contributing **this creator's particular role and scope**; observed source spellings; supporting issue titles. Alias references to the same canonical issue count once. Missing references do not invent creator links. |
| `publication_year_proxy`, `publication_year_end_proxy`, `year_basis` | Earliest/latest year for that role-specific contributing reference set. `actual_publication_year` requires actual years on all those references; otherwise complete cover years give `cover_year_proxy`; otherwise `unknown` and missing endpoints. This clock can differ from the whole reading's start, and it does not mix partial actual dates with partial cover dates. |
| `actual_publication_year_reference_count`, `cover_year_reference_count` | Number of distinct contributing references with each date type, for auditing the clock denominator. |
| `age_at_publication_year_proxy`, `age_at_discussion_year_proxy` | Corresponding context calendar year minus interpreted birth year. Publication uses the role-specific earliest contributing year; discussion uses the episode year. These are year-difference proxies, not age in completed birthdays, composition dates, or age throughout every issue in a long reading. |
| `posthumous_publication_year`, `posthumous_discussion_year` | Nullable flags: true when the context year is later than a known death year, false when earlier, unknown when dates are unavailable or context and death fall in the same year. They are not general living/dead labels; a missing death record does not establish that someone was alive. |
| `age_at_publication_status`, `age_at_discussion_status` | `year_difference_proxy`, `after_recorded_death_year`, `same_death_year_order_unknown`, `before_birth_year`, `implausible_age`, or `unknown_date`. Ages are suppressed after a recorded death year, in that same year when ordering is unknown, outside 0–110, and when required dates are absent. Reviewed organizations have no interpreted birth year or personal age. |

One creator may have several roles on an entry; one role can have many creators. Deduplicate appropriately before a person-level summary, and aggregate back to the ranked-entry unit before treating features as independent model rows. Publication clocks refer to observed credits; reprints and later editions can be posthumous without implying new work by the deceased creator.

### creator_awards.csv

The unique key is **`(creator_id, event_id)`**. Join `creator_id` to creators and `event_id` to `award_events.csv`.

| Columns | Definition |
|---|---|
| `creator_id`, `event_id`, `award`, `award_year`, `category` | Credited cluster, official event identity, Eisner/Kirby system, award year and original category. Recipient matching reuses the same official winner pages with the full eight-role credit-name universe, including cover-only contributors. |
| `recipient_scope`, `recipient_name` | `personal` craft category or `honor`, and matched recipient-name label(s). Work/series/edition winners are deliberately excluded from this relation. Names are matched labels, not necessarily literal spellings printed on the official page. Reviewed organization clusters are excluded from personal-award matching; parenthetical company affiliations are not promoted to personal recipients. A matched unclassified cluster still does not independently certify a natural-person identity. |

For a prior-recognition feature, join event years to the appropriate bridge clock and require `award_year < publication_year_proxy` or the chosen discussion year. Retain award-window eligibility; do not simply attach lifetime totals to old books. Craft-specific analysis must also check the award category's `winning_roles` in the event audit and the contributor's role. Joint craft-category winners do not establish every recipient's separate duty. Story-level award aggregates have their own credit scope and distinct-event counting; summing creator totals can double-count shared wins and contributors appearing in several roles.

## Selected narrative texts: story_texts.csv

This separate **2,637-row × 15-column** table preserves full available cleaned wiki `SynopsisN` prose for selected indexed narratives. It contains **1,711 available texts**, 703,219 whitespace-delimited words, and no length cap. Explicit reception sections and verified anthology credit boilerplate are removed; the longest text has 14,583 characters. Availability reaches 587 ranked entries; 481 have available text for every selected narrative and a known-complete reading list. Those are source-availability measures, not certification that every plot detail was summarized.

One row represents `(story_id, requested_title, substory_index)`. An unresolved reference receives one row with a missing index and no guessed first-story text. The table deliberately does not concatenate a reading into an ordered arc.

| Columns | Definition |
|---|---|
| `story_id`, `requested_title`, `wiki_title`, `issue_id` | Ranked-entry key, reference key, and resolved title/ID of the **ranked reference**. Join the first two keys to `issues.csv`; missing canonical metadata remains missing. |
| `substory_index`, `substory_title` | Selected numbered narrative slot in the ranked reference and its source title. An indexed narrative can be untitled; a missing index instead marks unresolved selection. |
| `synopsis_text`, `synopsis_word_count` | Full available wiki synopsis after markup, image captions, citations and placeholder instructions are removed; paragraphs remain. Count is whitespace-delimited cleaned words, zero when no text survives. This is fan-written plot description, not the comic's dialogue, captions or original illustrated prose; zero does not mean a silent comic. |
| `text_status` | `available` means non-placeholder cleaned prose exists; `missing_synopsis` means none was recovered; `unresolved_substory_selection` means no defensible narrative was selected; `missing_cached_transclusion` means an explicit source target/index was not cached. Additional parser outcomes are `stale_selected_substory_index`, `invalid_cached_transclusion`, `cyclic_cached_transclusion`, and `partial_or_multiple_cached_transclusion`. A partial transclusion outcome can retain local prose without claiming the referenced text is complete. |
| `source_substory_index`, `source_url` | Actual synopsis-source slot and page. Explicit `StoryGrab` references are followed only to already cached target/index pairs, never a guessed first story. Source index/page can differ from the ranked reference's `substory_index`/`wiki_title`. |
| `revision_id`, `revision_timestamp`, `revision_url` | Exact revision identity, source revision time and permanent URL for the actual synopsis source. This can differ from the ranked issue's metadata revision when text is transcluded. |
| `source_license` | Source-attributed CC-BY-SA notice with the applicable Fandom licensing link. It does not license publisher artwork or the original comic text. Preserve source/revision attribution and follow the linked terms when redistributing adaptations. |

`reports/texts_validation.json` records missing statuses, availability and duplicate-source checks. The same narrative or exact synopsis can appear in several ranked readings: retain shared-source and duplicate-text groups together when validating future NLP models, beyond ordinary issue/episode grouping. A model using these texts measures properties of the summaries; dialogue density, prose style and panel composition require the actual comics.

The notebook text experiment joins available synopses into unordered word bags without changing this table. It retains coverage controls and groups shared source narratives or normalized identical text during validation. Descriptive nearest-summary examples use only readings with every selected synopsis present.

## Curated tables

`award_events.csv`, `animal_watch.csv`, `story_labels.csv`, `hatter_story_roles.csv`, and `creator_watch.csv` are small reviewed tables shipped with the dataset; their columns are described in `kaggle-table-metadata.json` and on the Kaggle data page.
