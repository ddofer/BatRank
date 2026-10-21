# BatChat on Kaggle

The dataset and notebooks are private drafts on **danofer**.

- [Dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings)
- [Start with the EDA](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories): writers, years, heroes, villains, and word clouds.
- [Compare audiences](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree): BatChat, Goodreads, and RoundUp.
- [Predict the rankings](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories): regression and plot words.

## Run or reuse

Open a notebook and choose **Copy & Edit**, then **Run All** on CPU. The dataset is attached. The analysis reads saved files; it needs no scraping or API keys. Results go to `/kaggle/working/reports`.

For local use, clone [BatRank](https://github.com/ddofer/BatRank) and download the dataset from Kaggle. Follow the [README](../README.md). Local versions are pinned in `uv.lock`; the Kaggle setup cell prints its installed package versions.

The [copy-and-paste pack](kaggle-notebook-copy.md) contains titles, introductions, and a dataset description. The [data dictionary](data_dictionary.md) explains fields and joins. [Table metadata](kaggle-table-metadata.json) describes all 323 columns. Kaggle accepted the metadata update but did not return the file or column descriptions, so use the bundled dictionary if the Data Explorer omits them.

## Sources and illustration

Sources retain their own terms. Redistribution rights for the combined bundle remain unresolved; its Kaggle license is recorded as `unknown`. See the [source notes](enrichment_research.md). Private upload does not settle those rights.

The dataset contains no comic art. The EDA includes one attributed 250×385 *Ego* thumbnail beside commentary on its composition. Noncommercial use alone does not establish fair use. [U.S. Copyright Office guidance](https://www.copyright.gov/fair-use/)
