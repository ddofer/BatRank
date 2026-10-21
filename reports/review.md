# Data, analysis and editorial review

This is the technical audit trail for BatRank. For the reader-facing analyses, start with [the comics EDA](../notebooks/2.0-batchat-the-art-of-gotham.ipynb), [the prediction experiment](../notebooks/1.0-batchat-rankings.ipynb), or [the audience comparison](../notebooks/3.0-batchat-versus-the-crowd.ipynb).

The coverage and model tables below summarize the snapshot. Later sections record individual checks and revisions. They retain implementation details so that another analyst can audit the work.

Reviewed the expanded 2026-10-21 snapshot: extraction and join code, source mappings, two core tables, joined creator/text tables, three executed notebooks, generated reports and figures. Separate agents researched catalogue/API access and award records, checked the statistical comparisons and comics facts, and rewrote the notebook prose. This is a targeted independent review plus automated checks, not a manual audit of every comic or credit.

## Coverage after expansion

| Check | Result |
|---|---:|
| Ranked readings preserved | 740 |
| Printed source rank repeats / differs from page order | 24 / 470 rows |
| Story–issue references | 2,434 |
| Matched references / distinct wiki issue IDs | 2,425 / 2,390 |
| Complete resolved reading lists | 719 |
| All listed references attributed to ranked substories | 688 |
| Fully covered narrative writer/penciler credits | 685 |
| Narrative writer / penciler / colorist / letterer data | 723 / 726 / 644 / 698 |
| Featured cast / antagonist data | 725 / 607 |
| Collection links | 533 |
| Cover-age / complete actual-publication-age proxies | 730 / 146 |
| Eligible pre-publication Eisner window / observed personal win | 587 / 153 |
| Selected GCD narrative records / complete original-reading totals | 30 / 17 |
| Official publisher edition fallbacks | 5 |
| Goodreads named-narrative comparison | 40 |
| Strict RoundUp reader / critic comparison after vote filters | 110 / 78 |

Seven readings lack a usable wiki issue match: *Black & White Vol. 3*, *The Jiro Kuwata Batmanga Vol. 1*, *Draining*, *Disordered Minds*, *JLApe*, *Spawn/Batman* and *Through the Looking Glass*. Two other readings have an unmatched reference. Publisher information supplements some of these without supplying fictional narrative credits or treating a collection as a story. `validation.json` lists exact unresolved references and feature coverage.

The source's duplicated rank numbers remain in `source_rank`; unique page order is `rank`. No source entry is dropped. Joins enforce one story key and unique story/reference pairs. Full parsed snapshots must match both key sets before attachment; the intentionally partial catalogue sample is separately validated. A stale snapshot cannot silently attach to a changed reading list.

## Findings caught and fixed

- **Substory selection:** indexed narrative credits replace whole-issue unions where attributable. Reviewed mappings isolate *Manhunter*, the paired Batman #219 stories and *Cheer*. Unrelated reprints/backups retain their whole-issue credits but leave the narrative-specific columns. Multiple selected narratives do not create false writer/artist overlap or self-inking.
- **Cast parsing:** colonless headings, nested mention/flashback modes, annotation links, ordinary appearances plus flashbacks, character names such as Vision, N/A credits and blank story titles are covered. Locations alone do not establish character coverage. Cast entities preserve canonical target/continuity qualifiers and explicit unresolved scope.
- **Team stability:** transitions compare adjacent known teams in reading-list order, without bridging unknown references. Dominant-share and self-inking denominators are explicit. The team EDA excludes references selecting multiple narratives and stratifies by issue count.
- **Bibliography:** official DC contents resolve *Injustice* Volume 1 to print #1–6. GCD/wiki checks correct *The Museum of Mixed-Up Men* from the source's #313 to Detective #331, retaining the source label and cross-source credit disagreement. *Draining* is not aliased to its replacement story in Gotham Knights #12.
- **Units:** GCD narrative pages, fractional pages, sampled partial totals, reprint observations and complete original-reading totals remain separate. Publisher physical pages and edition dates never fill original narrative length/date. Collection notes do not certify every substory's reprint history.
- **Award meaning and time:** personal craft recipients are separate from work/series/design/archival prizes and Hall of Fame. Pre-publication counts exclude same-year awards. No ceremony in 1990 and the unreviewed 2026 results are not treated as negative evidence. Earlier books have missing pre-Eisner windows. Complete actual-publication years take precedence; otherwise the cover-year basis is explicit.
- **Model comparisons:** every model uses raw global ranks, including held-out subsets. Connected episode/shared-issue groups are stable under row order. Encoders and vocabularies fit inside folds. Award comparisons share creator-count/window controls. External-score comparisons share availability indicators and vote-intensity controls; automatic duplicate missingness indicators cannot alter Ridge's penalty. Permutations preserve observed/missing patterns and feature eligibility.
- **Outside score scope:** whole-issue ratings are excluded from strict comparisons when unrelated indexed narratives remain. Summed counts are issue-review observations; mean per-issue vote intensity controls reading length, while minimum counts screen reliability. Cohort sizes accompany threshold sensitivity.
- **Presentation:** all notebook markdown was rewritten around observed results. Comics claims have sources; neither excerpts nor summaries stand in for page-level visual analysis. A legend obscuring White Knight was moved. Prediction compression is described correctly, and obsolete charts/results were removed.

## Predictive evidence

All seven fixed models use the same five episode/shared-issue-isolated folds: 231 connected groups, largest 13 readings.

| Model | MAE, rank places | Pooled R² |
|---|---:|---:|
| Mean baseline | 185.48 | −0.005 |
| Era / format | 177.90 | 0.044 |
| Whole-issue credits | 169.04 | 0.118 |
| Attributed narrative credits | 170.90 | 0.097 |
| Narrative credits + cast/craft | 170.27 | 0.098 |
| Expanded + prior personal awards | 169.49 | 0.103 |
| Expanded random forest | 173.42 | 0.082 |

Cast/craft gain is **0.62 places [−1.88, 3.04]**; adding prior awards gives **0.78 [−2.04, 3.32]**. The expanded model does not beat whole-issue credits: gain **−0.46 [−4.27, 3.31]**. These are paired 95% connected-group bootstrap intervals on fixed out-of-fold losses, without refitting uncertainty. They do not support a reliable accuracy gain from the richer blocks. The richer data still improve attribution and descriptive analysis.

The later-discussion holdout starts 2025-08-07, with 573 training and 149 test readings after group purging. Its MAE is **140.88 versus 143.58**, with R² **−0.028**. Artist holdouts vary; Kelley Jones transfer is worse than its baseline. Lower error on a different cohort is not proof of stronger generalization. These tests use today's ranking, not historical rank snapshots.

Outside scores reduce MAE from **166.93 to 166.38** after metadata, availability and vote controls: gain **0.55 [−1.10, 2.12]**. Current scores can postdate the podcast. Correlations are audience/cohort-specific, and percentile gaps are within matched cohorts. Neither gaps nor aggregate ratings measure within-audience polarization.

Prediction mismatches are model errors worth inspecting, not automatically justified rerankings. Creator-event hits are historically confounded and can be editorial/backup contributions; they cannot establish misconduct-related ranking penalties.

## Verification and limits

**89 focused tests pass**, plus Ruff lint and formatting. Tests cover source parsing, HTTP/cache failures, anthology attribution, cast modes, team denominators, award clocks/classification, catalogue scope, stale joins, grouped validation and subset target units. All three notebooks execute with assertions and finite out-of-fold predictions. A complete rebuild of parsed enrichments and both canonical tables from cached sources produces byte-identical CSVs. The notebook editor preserved executed calculations while rewriting prose; affected plot cells were subsequently executed again. All current figures received an independent visual review.

Metron needs credentials and its challenged UI was not bypassed. Direct GCD requests returned 403; sampled indexed primary records can be stale or clipped, and the sample was deliberately selected. No all-row manual credit/cast verification, complete creator-event investigation, interior-art feature extraction or live cover-link audit was performed. Award zeros are limited to the reviewed universe; missing work matches remain unreviewed. Historical rank trajectories and individual audience-rating distributions are unavailable.

Publication/redistribution permission is not established by successful extraction. Source-specific wiki/GCD share-alike and attribution requirements, ranking/rating terms and separate image rights remain relevant. Raw responses and downloaded covers are excluded from the compact upload bundles. The files were initially prepared for local inspection. The private Kaggle uploads are documented in `kaggle-upload.json`.


## Joined creator features and uncapped synopses

The extension adds three creator relations and a synopsis table while preserving the core story/issue schemas. There are **1,847 creator credit clusters**, **19,466 unique story/creator/role/scope links** and **311 personal/honor award links** across 162 clusters. The 265-row award-event audit resolves all link IDs and retains the original work-event records. Birth years cover 933 creator clusters; gender assertions cover 1,685, with source revisions and missingness retained.

Independent review caught two consequential entity issues. Heroic Age's 1992 staff-template birth year is a studio founding year. Sixteen verified organizations now have no interpreted personal birth/death, gender or age, while raw source-year values remain auditable. Exact source redirects identify credit clusters rather than proving that every raw credited name is an individual person. Olyoptics in an official award recipient's parenthetical affiliation is excluded from personal recipient matching; studio profiles do not receive personal prize counts. Personal, Hall of Fame and work awards remain distinct.

Contributor-specific age clocks prefer complete actual-publication years, otherwise complete cover years, for only that person's role-contributing references. Known posthumous years and same-death-year ordering ambiguities receive missing ages. Tests cover nullable years and partial birthdays; source dates retain day/month/year precision rather than invented January birthdays. Current source gender labels are not inferred from names, independently verified self-descriptions or historical-at-publication measurements.

The full-text export contains **2,637 rows**, with **1,711 available synopses totaling 703,219 words**. There is **no character or word cap**: the longest field contains 14,583 characters. Text is available for 587 ranked readings; 481 have every selected synopsis present plus a known complete reading list. This availability flag does not establish that a source synopsis exhaustively covers its plot. Missing synopses, unresolved anthology selections and one uncached explicit transclusion remain flagged. Four shared source-narrative units occur across eight rows; future NLP validation must keep shared/duplicate texts together. The original text export added no ordering scaffold or NLP model. The later bag-of-words experiment is described below.

Thirteen text tests verify untruncated prose, paragraph preservation, placeholder/citation filtering, source attribution, transclusion cycles and missingness. Twelve creator-relation tests and four biography/age tests cover aliases, roles, clocks and award links, with a further award-index regression test for studio affiliations. The updated second notebook executes the joined creator-age/era comparison and full-synopsis coverage checks. Existing metadata-model feature frames are exactly unchanged by the studio-award correction, so their reported predictions remain applicable.

The synopsis corpus is wiki contributors' prose with applicable attribution/share-alike terms, not comic dialogue or a measure of page-level visual style. Full texts and creator features are included in the revised dataset archive with their provenance; raw source responses and comic art remain excluded.


## Shareable notebook revision

All three notebooks were revised again for comics readers and data scientists. A separate editor rewrote the first and third notebooks. The second now leads with concrete credit, character and storytelling examples. Methods stay beside the comparisons they qualify. A separate statistical reviewer checked the new analyses and the existing validation design.

Three additions use the existing snapshot:

- **Credit concentration:** 589 complete, fully attributed readings have all six narrative credit roles. Each reading allocates one unit per role equally across its canonical credit entities. The five leading letterer credits receive 34.6% of the allocation, against 9.5% for pencilers and 18.3% for writers. This is neither a workload estimate nor industry market share. All roles use the same readings; the sample still favors books with complete records.
- **Plot coverage by era:** 23/69 readings from the 2020s have any selected synopsis, compared with 67/69 from the 1980s. Complete selected-text coverage is 8/69 versus 59/69. Seven unknown-era readings are reported separately. Missing text can encode publication era in a future NLP model; this snapshot cannot establish why coverage differs.
- **Same-book audience comparison:** 69 readings pass both reader and critic screens. BatChat's Spearman correlations are 0.181 with readers and 0.155 with critics. The paired difference is 0.025, with a 95% connected-group bootstrap interval of −0.224 to 0.303. Readers and critics correlate 0.437 with each other. Critic-minus-reader score gaps change by publication era, but reviewer composition and scoring histories remain inseparable from taste.

Figures now include labeled model-error dots, paired improvement intervals, within-length team distributions, credit concentration, plot coverage by decade, and the same-book audience comparison. Chart descriptions are retained as alt text. The HTML renderer relocates local links, so companion links open rendered notebooks and documentation links resolve from the report directory. A small regression test covers those links and preserves external URLs, anchors and image descriptions.

All three revised notebooks were executed from the saved data. Updated HTML and both ZIP bundles were regenerated after execution. No ranking refresh, new external scraping or NLP model was added in this revision.


## Popular-audience and text-model revision

The three notebooks now explain the questions and results before the statistical details. The comics and audience notebooks received another independent prose and visualization pass. Dense diagnostic tables are still exported as CSVs. They no longer interrupt the main reading flow. HTML exports hide code and retain readable methods notes; the source notebooks keep every calculation.

The text audit found three contaminated synopsis fields. Arkham Asylum contained an explicitly headed reception section with outside rankings. Black and White #2 and #3 contained anthology introductions and credit labels. Targeted extraction fixes removed 306 non-plot words. The other 2,634 rows remain identical. Full plot text remains uncapped. The corpus now has 703,219 words; availability remains 1,711 synopsis fields, 587 readings with text, and 481 readings with every selected synopsis present. Tests distinguish reception headings from plot references to a reception desk, preserve later plot sections, and keep Bat-Mite's actual creator-related metafiction.

The new model uses TF-IDF unigrams, avoiding artificial two-word phrases across joined synopsis boundaries. Vocabulary and IDF fit inside training folds. Five outer folds evaluate predictions while keeping connected episode, issue, and text groups together. Each outer training set uses three grouped inner folds to choose Ridge alpha from 1, 10, and 100. All compared models use the same partitions and candidate penalties. Shared source narratives and normalized duplicate text join the group graph; this snapshot still has 231 groups. Explicit controls include text availability, complete selected-text coverage, available fraction, log word count, and log selected-unit count.

| Evaluation rows | n | Coverage-controlled MAE | With words | Gain | 95% group-bootstrap interval |
|---|---:|---:|---:|---:|---:|
| All readings | 740 | 170.876 | 170.567 | 0.310 | −0.010 to 0.634 |
| Some text | 587 | 169.584 | 169.187 | 0.397 | 0.001 to 0.783 |
| All selected plots present | 481 | 175.210 | 174.867 | 0.343 | −0.094 to 0.770 |

The some-text interval barely clears zero. Its estimated gain remains below half a rank place. Subset rows evaluate predictions from the models trained on all readings; these are not complete-case-only training experiments. Intervals resample saved grouped errors and exclude refitting uncertainty. Plot words alone have MAE 179.181, against 185.479 for a mean guess. The earlier fixed-alpha metadata benchmark is a separate experiment, not the control for these tuned text models.

An independent statistical reviewer checked the implementation and reproduced gains from saved predictions. The model reads fan-written summaries, not comic dialogue or visual storytelling. The results do not establish that plot is unimportant, or that a richer text model could not help.

Descriptive nearest-summary examples use only the 481 readings with complete selected-text availability. The three anchors are the previously discussed formal examples Undone, Ego, and The Clown at Midnight. Candidates in the same connected group are excluded. Corpus-wide IDF is appropriate here because this is descriptive retrieval; it never enters predictive validation. Similarity is lexical and modest. The plots show shared words and both ranks, without claiming near-identical stories or equivalent quality.

The Kaggle guide supplies dataset listing copy, notebook descriptions and upload/attachment instructions checked against official documentation. The new `make share` command renders HTML and rebuilds both bundles, verifying archive contents against local files. The initial review covered local execution. The later private uploads use Kaggle URLs for companion notebooks and documentation; see `kaggle-upload.json` for their run status.


## Final EDA and runtime pass

The shorter README links to the detailed methods instead of repeating them. The audience-correlation bootstrap now samples two-column NumPy arrays instead of wide DataFrames. Its measured cell time fell from 80.31 to 1.34 seconds in local runs. All three correlations and six interval endpoints are exactly unchanged. A regression test covers tied ranks, unequal group sizes and nonconsecutive row indices.

The EDA now opens with frequent writers (677 eligible readings) and publication-decade rank distributions (733 readings with known cover-start years). The complete antagonist table includes 1,487 entries and 3,102 reading–entry links across 559 readings. Of these entries, 1,104 appear once. Gangs and unnamed characters remain explicit. Best/worst story titles are exported alongside counts and rank distributions.

A descriptive sensitivity check compares twelve frequent antagonists within decade and issue-count bands. Each retained stratum contains at least three readings with the antagonist credit and three without. Pooled and stratified gaps use identical retained readings. Stratified gaps weight by the antagonist's reading count. They do not control for creators, co-occurring villains or selection by the podcast. An independent reviewer reproduced antagonist counts, medians and example titles, and checked the cohort construction. The two new figures were visually inspected. No causal or significance claim is made.

## Mad Hatter cast-credit audit

The [34-reading audit](hatter_credit_audit.csv) checks the Mad Hatter examples against cached source revisions. It uses the EDA cohort: selected-narrative cast attribution and complete issue-level cast coverage. Every credited reference contains an ordinary antagonist entry for a Jervis Tetch identity in a selected narrative. The source revision IDs match the issue table. The audit preserves revision links, total references, and credited references for each reading. Explicit mention, cameo, depiction, and flashback-only entries do not qualify. No incorrect Hatter inclusion was found in these 34 readings.

The result describes books with an antagonist credit. It does not identify their principal villain. Hatter is credited in 3 of 13 references for *The Long Halloween* (#4), 2 of 14 for *Dark Victory* (#16), and 1 of 13 for *Final Crisis* (#26). The cached [Final Crisis #2 synopsis](https://dc.fandom.com/wiki/Final_Crisis_Vol_1_2?oldid=3888245) describes Turpin interrogating him. Hatter-centered examples cover a much wider range: *Unknowing* (#142), *Madness* (#164), *The Scoop of the Century* (#478), and *Mad* (#733). Their plots support that description; see the audit's source revisions, including [Unknowing's opening issue](https://dc.fandom.com/wiki/Detective_Comics_Vol_1_758?oldid=3322601) and [Mad's opening issue](https://dc.fandom.com/wiki/Batman:_The_Dark_Knight_Vol_2_16?oldid=3950419).

The favorable median does **not** disappear in a simple coverage check. All 34 readings have median rank 183.5. The 11 readings with Hatter credited in every reference have median 183. The 13 with credits in at least half their references also have median 183. These checks retain anthologies and other ensemble books; they do not measure panel time or narrative importance. Cast centrality, creators, co-occurring characters, and podcast selection remain unresolved explanations.

The earlier first-place comparison applied only to twelve frequently credited entries. It was not a ranking of every villain: Edward Nashton has median 183 across 21 readings outside that selection. Canonical source names also distinguish Nashton, Nygma, and Nigma variants. Removing a universe qualifier does not establish that all aliases have been reconciled. No live source refresh or comic-page inspection was performed for this audit.


## Narrative and cast-atlas revision

All three notebooks now build a continuous argument, with their own dataset orientation and interpretation beside each figure. Two independent editors rewrote the prediction and audience notebooks. The EDA received a full rewrite and a separate editorial check. Its cast chart compares the 15 most frequent featured and antagonist entries on the same rank scale. Complete exports contain 531 featured entries and 1,487 antagonist entries. The larger atlas shows all 75 featured and 95 antagonist entries with at least five readings, using row-normalized rank distributions. Assertions check every histogram denominator.

The Hatter result is now an audited example of the distinction between cast presence and narrative importance. The notebook retains the favorable median and the all-issues sensitivity result without declaring Hatter the best villain or claiming that ensemble appearances explain away the association. Canonical alias limitations remain explicit.

One source-sized Ego thumbnail is embedded in the EDA beside commentary on its composition. The notebook retains artist credit and source links. It is not part of the dataset's image files. This changes the earlier notebook-bundle exclusion of all comic art; the core dataset still contains no comic images. U.S. noncommercial fair-use considerations are linked in the sharing guide, without treating them as blanket permission for the dataset.


## Metric-direction audit

All three notebooks now label rank preference separately from prediction accuracy. Displayed table headers identify lower-is-better ranks/errors and higher-is-better ratings. Difference plots state the subtraction order and the meaning of the sign; permutation importance explicitly means prediction degradation after shuffling. A collapsible key in each notebook links to the dictionary's full metric definitions, including the opposite directions of rank percentiles and audience preference positions. Neutral quantities such as counts and disagreement are not labeled as quality scores.

The notebooks were executed again, and signed-gap figure layouts were visually checked. Numeric report comparisons passed at absolute tolerance 1e-10. Only two CSVs changed at floating-point roundoff scale (maximum observed change below 2e-13); other numeric exports are byte-identical. No data definitions or analytical calculations were changed.


## Shaped plot-vocabulary clouds

The EDA adds a bat-shaped document-frequency cloud and question-mark/umbrella comparisons for Riddler and Penguin. The bat uses 481 complete-summary readings. Character comparisons also require complete selected-narrative cast coverage, leaving 478 readings: 32 Riddler versus 446 others, and 41 Penguin versus 437 others. Riddler's Nashton/Nigma/Nygma aliases are combined explicitly for this analysis only. Each word counts at most once per reading.

Villain word size uses the log2 ratio of add-one-smoothed document prevalence. Only positive ratios supported by at least five cohort readings enter the clouds. The two panels scale separately. No rank or rating enters selection or weighting. Exports retain word counts, denominators, scores, and cohort membership. The geometric masks are generated locally; no additional artwork is downloaded. WordCloud 1.9.6 is pinned in the environment.

An independent reviewer reproduced the quoted word counts and summary-length medians and inspected both figures. The narrative explains why ensemble casts, longer summaries, small counts, and wiki narration prevent treating the clouds as causal or quality measures. Small-word contrast was increased after visual review. Notebook assertions check binary per-reading counts, nonempty masks, disjoint complete-cast comparison groups, minimum support, and finite scores.

## BatRank sharing update — 22 October 2026

All three notebooks completed on Kaggle. EDA tables match the local results. Kaggle uses NumPy 2.1.3, pandas 2.3.3, SciPy 1.16.3, scikit-learn 1.6.1, Matplotlib 3.10.0, and WordCloud 1.9.6. Compared with the pinned local environment, main-model and text-model MAEs differ by less than 0.005 rank places. Artist-holdout errors differ by less than 0.031 places. These differences do not change the conclusions. The later EDA revision moves writers, years, heroes, and villains first and removes the attribution and collection-link digressions.

The README links Dan Ofer’s Scholar profile and the original ComicsXF rankings. The six CSVs stay on Kaggle; GitHub contains code, notebooks, figures, reference files, and tests. All 89 tests pass. The sharing bundles contain table descriptions for all 323 columns.
