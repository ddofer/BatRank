# Award enrichment: what won, who won, and when

This snapshot records the official **Eisner winners for 1988–2025** and the predecessor **Kirby winners for 1985–1987**. There was no Eisner ceremony in 1990. The 2020s archive ends at 2025: 2026 is outside this reviewed source set, regardless of the dataset retrieval date.

Official sources:

- [1980s: Kirby and early Eisner recipients](https://www.comic-con.org/awards/eisner-awards/past-recipients/past-recipients-1980s/)
- [1990s](https://www.comic-con.org/awards/eisner-awards/past-recipients/past-recipients-1990s/)
- [2000s](https://www.comic-con.org/awards/eisner-awards/past-recipients/past-recipients-2000s/)
- [2010s](https://www.comic-con.org/awards/eisner-awards/past-recipients/past-recipenties-2010s/)
- [2020–2025](https://www.comic-con.org/awards/eisner-awards/past-recipients/past-recipenties-2020s/)

`python -m scripts.awards --offline` regenerates the snapshot and audit CSV from the five cached official HTML pages. Omit `--offline` to fetch missing pages serially with caching and a two-second pause. Existing snapshots are reused. No nominees are counted.

## Scope and attribution

These are three different observations:

1. **A credited creator won a personal category**, possibly for an unrelated comic. For example, a colorist's award for Hellboy can be evidence of professional recognition when looking at that person's Batman work. It is not a Batman story award.
2. **A ranked work won an award.** These links are explicitly curated, with exact-work, contained-story, series-context, collected-edition, archival-edition and edition-design scopes. *Half a Life* won Best Serialized Story. The *Year One Artist's Edition* won archival/design categories decades after the original comic. A short story inside *DC Pride 2022* winning does not mean every story in that anthology won.
3. **A creator entered the Hall of Fame.** This is a career honor, including posthumous recognition, not another annual craft win. Hall-of-Fame totals count distinct matched inductees, whereas personal-win totals count distinct award events. A shared craft award is one event even if two credited collaborators won it together.

The selected-narrative credits are used when both `substory_attribution_coverage` and `narrative_credit_issue_coverage` equal one. Otherwise the feature falls back to whole-issue credits and says so in `awards_credit_scope`. Interior creative roles plus editor are included; cover-only contributors are excluded from this aggregate. An interior artist's own cover-category wins may still contribute to that creator's overall professional-recognition count. The role-specific columns restrict both the ranked work's credit and the winning category's craft scope. Joint writer/artist and penciler/inker categories do not reliably disaggregate individual recipients' duties; the event table preserves that category rather than inventing per-person roles.

Creator matching normalizes punctuation, accents and initial spacing, with explicit aliases for David/Dave Mazzucchelli, Denny/Dennis O'Neil, Sean/Sean Gordon Murphy, and Laura DePuy/Dupuy/Martin. Recipient names in the audit CSV are the matched names in the credited-creator universe, not a claim to enumerate every winner on an event. Original winner descriptions remain in the cached external snapshot.

## Time and missing values

`*_pre_publication` uses **award year strictly before publication year**. Actual publication years are preferred only when every listed issue has one: the minimum date of a partly dated arc is not necessarily its start. Otherwise the cover year is a stated proxy (`awards_publication_year_basis`). Same-year awards are excluded because the ordering within the year is not established. Features are missing for works published in or before 1988, rather than treating the absence of an established Eisner history as evidence of an unrecognized team. `awards_prepublication_observed_years` reports the size of the observable Eisner-year window; it excludes 1990.

`*_pre_discussion` similarly requires award year strictly before the episode's year. These features answer a retrospective reception question: what recognition had the team accumulated before the discussion? They are not interchangeable with recognition available when the comic first appeared. `*_after_discussion_year` explicitly separates later recognition. Current total award counts, work/edition totals and Hall-of-Fame totals are retrospective descriptors; do not feed them into a purported historical prediction without an appropriate cutoff.

`work_awards_match_status = not_exhaustively_reviewed` means zero curated work matches, **not** a verified absence of work awards. The five archive pages cover a clear award universe; they do not cover Harvey, Ringo, Inkpot, international awards, nominations, or lifetime honors administered outside the listed Hall of Fame. Likewise, a zero creator count means no matched event in this reviewed universe, not "this person has never won a prize."

## Files and validation

- `data/external/awards.json`: full parsed winner events, source hashes, observed years and one feature record per ranked story.
- `data/external/award_events.csv`: only the award events referenced by exported story features or curated work matches, including year, category, matched recipients, craft scope, awarded work and primary source URL.
- `creator_award_event_ids` and each `work_award_matches` entry join to that audit table's `event_id`.

Six focused parser tests cover the archive's h5 year heading, two categories in one list item, a category and winner split over adjacent list items, tied personal recipients, accented-name identity, whole-name boundaries, category scope, conservative year boundaries, missing pre-award history, and selected-narrative attribution. All source years 1985–2025 except 1990 must occur, and curated work links must resolve to exactly one official event. Offline generation needs no network.

For analysis, professional recognition is a useful covariate and a plausible confounder. It is also partly a function of era, career length, role and the number of credited people. `awards_credited_creator_count` and `creator_eisner_personal_award_holders_pre_publication` allow normalization for recorded crew size. A comparison should show eligible-year coverage, distinguish craft categories, and test whether any association survives publication-era controls and creator/issue-group separation. An award coefficient alone does not establish that prizes changed the podcast's judgment.


The joined creator extension re-indexes the same official winner records against all eight source-credit roles, including cover-only artists. `creator_awards.csv` links personal/honor recipients to creator IDs; the compact event audit now has 265 rows, retaining the story/work matches as well. Verified organizations in `creator_entity_types.json` are excluded from personal recipient matching: in particular, the parenthetical Olyoptics affiliation in the 1994 colorist winner text is not another independently awarded person. Creator lifetime totals are descriptive and require award-year filtering for publication-time models.
