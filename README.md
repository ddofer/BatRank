# BatRank

A Batman dataset built from [ComicsXF’s BatChat rankings](https://comicsxf.com/batchat-rankings/), with three notebooks on the stories, their creators, and the podcast’s taste.

**740 stories. Rank 1 is best. Snapshot: 21 October 2026.**

By **Dan Ofer** · [Google Scholar](https://scholar.google.com/citations?user=uDx2ItYAAAAJ) · [Kaggle](https://www.kaggle.com/danofer)

## Explore

| Notebook | What’s in it | Kaggle |
|---|---|---|
| [Batman stories: the EDA](notebooks/2.0-batchat-the-art-of-gotham.ipynb) | Best and worst-ranked creators and characters, series, Elseworlds, gorillas, sharks, and plot words | [Run](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories) |
| [BatChat vs the crowd](notebooks/3.0-batchat-versus-the-crowd.ipynb) | Where Goodreads readers, RoundUp readers, and critics disagree with the hosts | [Run](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree) |
| [Predicting the rankings](notebooks/1.0-batchat-rankings.ipynb) | Regression, plot words, and the stories the models get wrong | [Run](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories) |

Moench and Kelley Jones made both *Red Rain* (#6) and *Unseen* (#716). Mad Hatter appears in surprisingly well-ranked books. Goodreads prefers *White Knight* to *Red Rain*; BatChat strongly disagrees.

## Dataset

[Download on Kaggle](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings). The Kaggle dataset and notebooks are currently private drafts.

| File | Rows | Contents |
|---|---:|---|
| `stories.csv` | 740 | Rankings, writers, artists, characters, dates, awards, and outside ratings |
| `issues.csv` | 2,434 | Issues included in each story |
| `creators.csv` | 1,847 | Creator names, biographies, and awards; studios are flagged |
| `story_creators.csv` | 19,466 | Who worked on each story and in which role |
| `creator_awards.csv` | 311 | Creator-to-award links |
| `story_texts.csv` | 2,637 | Full plot summaries and records of missing text |

Two small tables in `data/external/` add [checked animal appearances](data/external/animal_watch.csv) and [explicit issue labels](data/external/story_labels.csv), including Elseworlds and named events. Both join on `story_id` and retain source links. Missing labels mean unknown.

Start with `stories.csv`. Join on `story_id` or `creator_id`. The [data dictionary](references/data_dictionary.md) explains the fields, joins, and missing values.

There are **1,711 plot summaries totaling 703,219 words**, with no length cap. Text covers 587 stories; 481 have complete summaries and issue lists. Recent comics have less coverage. Outside ratings cover selected books and editions. The notebooks check those matches before comparing scores.

## Run locally

Download the dataset from Kaggle and place its six CSVs in `data/processed/`. The repository contains the helpers and reference files.

```bash
uv sync --locked
make insights    # EDA
make compare     # audience comparisons
make analyze     # prediction
make check       # tests and lint
```

The notebooks use saved data. They need no scraping or API keys.

## Processing code

[scripts/dataset.py](scripts/dataset.py) downloads the ranking list and issue metadata. It caches responses and spaces requests. The other [scripts](scripts/) add characters, awards, creator details, ratings, and plot summaries. [tests/](tests/) covers parsing, joins, and analysis checks.

`make data` fetches the core data. The full enrichment also uses reviewed mappings and source caches; see the [source notes](references/enrichment_research.md) and [audit](reports/review.md). Raw caches and full plot text are kept out of GitHub.

## Sources

Rankings are by **Matt Lazorwitz and Will Nevin**, hosts of [BatChat at ComicsXF](https://comicsxf.com/batchat-rankings/). Issue details and summaries come mainly from [DC Database](https://dc.fandom.com/). Other sources include [Comic-Con’s Eisner archives](https://www.comic-con.org/awards/eisner-awards/), [Grand Comics Database](https://www.comics.org/), [DC](https://www.dc.com/), [Goodreads](https://www.goodreads.com/), and [Comic Book RoundUp](https://comicbookroundup.com/). Source links remain in the tables.

This is an independent project. Sources retain their own terms; the combined dataset is not CC0. The EDA includes one attributed *Ego* thumbnail for commentary on its composition.
