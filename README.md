# BatRank

A Batman dataset built from [ComicsXF’s BatChat rankings](https://comicsxf.com/batchat-rankings/), with seven notebooks on the stories, their creators, the podcast’s taste, and what drives it.

**740 stories. Rank 1 is best. Snapshot: 21 October 2026.**

By **Dan Ofer** · [Google Scholar](https://scholar.google.com/citations?user=uDx2ItYAAAAJ) · [Kaggle](https://www.kaggle.com/danofer)

## Explore

| Notebook | What’s in it | Kaggle |
|---|---|---|
| [Who gets the good Batman stories?](notebooks/2.0-batchat-the-art-of-gotham.ipynb) | Writers, artists, letterers, eras, writer–artist pairs, cited controversy examples | [Run](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories) |
| [Gotham's rogues, ranked](notebooks/2.1-batchat-gothams-rogues.ipynb) | Heroes and villains by rank, the Mad Hatter trick, gorillas and sharks, villain word clouds | [Run](https://www.kaggle.com/code/danofer/gotham-s-rogues-ranked) |
| [What Batman plots are made of](notebooks/2.2-batchat-plot-words.ipynb) | Series, Elseworlds, plot-summary coverage, plot ingredients, the bat word cloud | [Run](https://www.kaggle.com/code/danofer/what-batman-plots-are-made-of) |
| [BatChat vs the crowd](notebooks/3.0-batchat-versus-the-crowd.ipynb) | Where Goodreads readers, RoundUp readers, and critics disagree with the hosts | [Run](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree) |
| [Can a computer predict BatChat's favorites?](notebooks/1.0-batchat-rankings.ipynb) | Regression, plot words, and the stories the models get wrong | [Run](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories) |
| [Which stories deserve a second look?](notebooks/4.0-batchat-second-look.ipynb) | 20 held-out model disagreements, including ten early-episode case studies | [Run](https://www.kaggle.com/code/danofer/which-batman-stories-deserve-a-second-look) |
| [What pushes a story up the list?](notebooks/5.0-batchat-what-drives-the-ranking.ipynb) | Ridge and XGBoost, held-out SHAP, interactions, story counts and uncertainty | [Run](https://www.kaggle.com/code/danofer/what-pushes-a-batman-story-up-batchat-s-list) |

Moench and Kelley Jones made both *Red Rain* (#6) and *Unseen* (#716). Mad Hatter’s low median rank mostly comes from big-cast books and collections; the rogues notebook [checks his actual role](data/external/hatter_story_roles.csv). Goodreads prefers *White Knight* to *Red Rain*; BatChat strongly disagrees.

## Dataset

[Download on Kaggle](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings). Twelve flat CSVs; every column is described on the Kaggle data page.

| File | Rows | Contents |
|---|---:|---|
| `stories.csv` | 740 | 21 columns: rank and title first, selected-story credits, years and discussion links |
| `story_features.csv` | 740 | Cast, awards, outside ratings, coverage flags and provenance; join on `story_id` |
| `issues.csv` | 2,434 | Issues included in each story |
| `creators.csv` | 1,847 | Creator names, biographies, and awards; studios are flagged |
| `story_creators.csv` | 19,466 | Who worked on each story and in which role |
| `creator_awards.csv` | 311 | Creator-to-award links |
| `story_texts.csv` | 2,637 | Full plot summaries and records of missing text |

Five small curated tables join on `story_id`, `creator_id`, or `event_id`: `award_events.csv`, [animal_watch.csv](data/external/animal_watch.csv), [story_labels.csv](data/external/story_labels.csv), [hatter_story_roles.csv](data/external/hatter_story_roles.csv), and [creator_watch.csv](data/external/creator_watch.csv). Missing labels mean unknown.

Start with `stories.csv`; specialist columns are in `story_features.csv`. Join them one-to-one on `story_id`, or join creator tables on `creator_id`. The [data dictionary](references/data_dictionary.md) explains the fields, joins, and missing values.

There are **1,711 plot summaries totaling 703,219 words**, with no length cap. Text covers 587 stories; 481 have complete summaries and issue lists. Recent comics have less coverage. Outside ratings cover 70 Goodreads matches, 390 stories with RoundUp reader ratings, and 227 with critic ratings. Strict same-story and review-count checks leave cohorts of 52, 147, and 110. The [acquisition audit](references/enrichment_research.md#ratings-acquisition-coverage-audit) explains the remaining gaps.

Notebook tables show at most 20 rows, with labeled previews for longer tables. The CSV exports retain all records. [Dataset validation](reports/validation.json) and [ratings validation](reports/ratings_validation.json) record coverage, unresolved matches and rejected rating links.

## Run locally

The easiest way to run the notebooks is through their Kaggle links above, with the dataset attached. To run locally, download the [Kaggle dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings) into `data/kaggle/` so that `data/kaggle/stories.csv` exists. If the full archive is unavailable, download the twelve CSVs individually from the dataset’s Data Explorer. The notebooks also find the attached dataset under `/kaggle/input` when run on Kaggle.

```bash
uv sync --locked
make notebooks   # execute the notebooks; save each only after a successful run
make check       # tests and lint
```

The `.ipynb` files are the notebook sources; there are no parallel `.py` copies. They run offline against the staged tables using the dependencies in `pyproject.toml`. The artwork is embedded as an attributed attachment. Run one notebook with `uv run python scripts/execute_notebooks.py notebooks/2.2-batchat-plot-words.ipynb`.

## Processing code

[scripts/dataset.py](scripts/dataset.py) downloads the ranking list and issue metadata. It caches responses and spaces requests. The other [scripts](scripts/) add characters, awards, creator details, ratings, and plot summaries. [tests/](tests/) covers parsing and joins.

`make data` fetches the core data. The full enrichment also uses reviewed mappings and source caches; see the [source notes](references/enrichment_research.md). Raw caches and full plot text are kept out of GitHub.

Maintainers with the complete processed tables can run `make share` to rebuild `data/kaggle/` and its `dataset-metadata.json` for upload. A fresh clone does not include those processed tables; use the download above to run the notebooks.

## Sources

Rankings are by **Matt Lazorwitz and Will Nevin**, hosts of [BatChat at ComicsXF](https://comicsxf.com/batchat-rankings/). Issue details and summaries come mainly from [DC Database](https://dc.fandom.com/). Other sources include [Comic-Con’s Eisner archives](https://www.comic-con.org/awards/eisner-awards/), [Grand Comics Database](https://www.comics.org/), [DC](https://www.dc.com/), [Goodreads](https://www.goodreads.com/), and [Comic Book RoundUp](https://comicbookroundup.com/). Source links remain in the tables.

This is an independent project. Sources retain their own terms; the combined dataset is not CC0. The plot-words notebook includes one attributed *Ego* thumbnail for commentary on its composition.
