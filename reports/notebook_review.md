# Notebook and code review

A separate subagent reviewed each of the seven notebooks; another reviewed all processing scripts, tests, build configuration and local setup instructions. The integration pass checked the changes together and inspected regenerated figures. Review covered the current data snapshot, saved outputs, prose, numerical claims, readability and whether each section delivers a finding.

## What each notebook contributes

| Notebook | Reason to keep it | Corrections and polish |
|---|---|---|
| [Prediction](../notebooks/1.0-batchat-rankings.ipynb) | Shows how little metadata and summary vocabulary explain, with concrete reading comparisons. | Corrected unequal-fold mean absolute error aggregation; renamed a supposed words-only model that also uses format; restored an off-chart prediction. Explained the third similarity pair and separated descriptive similarity from prediction. |
| [Creators](../notebooks/2.0-batchat-the-art-of-gotham.ipynb) | Compares creative teams, consistency, publication eras and contrasting books by the same people. | Fixed a six-row table displaying only missing values and fractional ages entering the wrong age bands. Distinguished fractional credit shares from story counts. Added Brubaker's 16 stories all in the top 300. |
| [Rogues](../notebooks/2.1-batchat-gothams-rogues.ipynb) | Hatter's ensemble appearances show why a character leaderboard needs a role check; animal oddities keep the exploration playful. | Corrected the description of the matched era/length comparison. Separated overlapping gorilla/King Shark points, shortened labels cleanly and reduced the animal census to rank extremes and distinctive examples. Kept the complete guide in the dataset. |
| [Plot words](../notebooks/2.2-batchat-plot-words.ipynb) | Reveals text-coverage bias, misleading medians and what summaries lose about visual storytelling. | Removed the event table with no accompanying finding. Added the actual series contrast and vampire split. Removed generic narration verbs from both word-cloud notebooks; retained the attributed artwork and silent/prose comparison. |
| [Outside audiences](../notebooks/3.0-batchat-versus-the-crowd.ipynb) | Uses memorable book disagreements and the same-book sample to compare readers, critics and BatChat. | Corrected a chart that claimed to show the ten largest gaps but selected five per direction. Interpreted the weak matched correlations and the decade pattern, and clarified equal weighting of issue scores. |
| [Second looks](../notebooks/4.0-batchat-second-look.ipynb) | Twenty reviewed cases turn model disagreements into specific rereading questions, including early discussions. | Corrected claims about which creator inputs survive the frequency screen for *Ego* and *Night of the Stalker*. Clarified the timing flag. Removed three unused notes and replaced generic fallback text with an assertion requiring reviewed notes. |
| [Feature effects](../notebooks/5.0-batchat-what-drives-the-ranking.ipynb) | Distinguishes effect size, direction, prevalence and uncertainty with actual story and group counts. | Fixed title-based lookup that could conflate different stories with the same title. Explained scaled numeric coefficients, replaced stale case commentary and interpreted Morrison, Klein and Superman rather than only describing the machinery. Added units and separate-scale guidance to mismatch plots. |

## Shared code

- Dataset staging now completes all copies, projections and metadata before replacing an existing staged folder. A regression test reproduces the previous data loss when a source is missing or a schema is invalid, then verifies preservation after the fix.
- Declared BeautifulSoup, which three parsers already imported but a clean installation did not receive. Verified parser imports in an isolated environment.
- Removed the unused SHAP package and its heavy dependencies. The notebook retains the exact linear SHAP formula and its prediction-reconstruction assertion.
- Corrected fresh-clone instructions: notebook readers download the published tables; `make share` is for maintainers with processed inputs. Included an individual-file fallback for Kaggle's bulk-download failure.
- Kept small plotting helpers inside notebooks so each remains runnable on Kaggle without importing repository-only code. A new framework or notebook generator would add more maintenance than it removes.

## Verification and limits

All seven notebooks were executed after their changes. Numerical claims and the twenty selected case notes were checked against the current CSVs and relevant model inputs. The integration pass inspected regenerated charts, checked notebook structure and code, and retained the table limit below 25 rows. A regression check catches the formerly empty creator-credit table. All 90 tests, lint, formatting and lock-consistency checks pass; clean-environment parser imports also pass.

The twelve CSV exports are unchanged byte for byte. The review did not reacquire the external source websites or recreate their original matching decisions. Existing historical annotations retain their sources; one DC article rejected automated access. Models remain descriptive associations within one ranked snapshot, and a frequency threshold cannot separate a creator from a particular run or era.


## Bounded boosted-tree follow-up

The assumption was that one shallow XGBoost configuration would reduce held-out error by roughly five rank places and improve most folds. The same five linked-issue/episode folds, training-only encoders and eight-story vocabulary screen were reused. The CPU-only XGBoost 3.2.0 build used 200 trees, depth three, learning rate 0.05, minimum child weight 10, regularization 10 and 80% row/column sampling; there was no tuning search.

| Fold | Ridge error | XGBoost error |
|---|---:|---:|
| 1 | 174.30 | 168.09 |
| 2 | 182.22 | 177.17 |
| 3 | 173.65 | 167.85 |
| 4 | 174.74 | 172.64 |
| 5 | 165.73 | 162.04 |

Pooled error fell from **174.14 to 169.57**, about 4.6 places, with improvements in all five folds: supported within this snapshot, not an independent confirmation. This justified a compact nonlinear check in the feature-effects notebook, not a second boosting library or a parameter search. The initial smoke run used 20 trees and eight held-out examples before the full run. The feature panel pairs mean magnitudes with signed per-story contributions and input-value colors; its dot spread is story variation, not a confidence interval. Native TreeSHAP contributions reconstruct predictions; native interaction rows reconstruct those contributions. Both identities are asserted in the notebook.

Interaction screening is limited to pairs among the 20 most influential numeric/name inputs, with at least eight jointly observed stories, five linked groups and nonzero contributions in four fits. Era × length leads; the notebook shows observed rank medians beside the extra pair term and masks sparse cells. Credit-related interactions are much smaller and do not establish a creator-team effect. All tree explanations use held-out stories; continuity variants stay separate in the interaction screen.

Reproduce with `uv run python scripts/execute_notebooks.py notebooks/5.0-batchat-what-drives-the-ranking.ipynb`. The CPU package supplies TreeSHAP directly, without the separate SHAP package or GPU dependencies. The CSV exports are unchanged.
