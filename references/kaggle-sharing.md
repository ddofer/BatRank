# BatChat on Kaggle

- [Dataset](https://www.kaggle.com/datasets/danofer/batchat-batman-rankings): 11 flat CSVs with per-column descriptions (`references/kaggle-table-metadata.json`) and the About text (`references/kaggle-dataset-about.md`).
- [Who Gets the Good Batman Stories?](https://www.kaggle.com/code/danofer/who-gets-the-good-batman-stories)
- [BatChat vs the Crowd](https://www.kaggle.com/code/danofer/batchat-vs-the-crowd-where-batman-fans-disagree)
- [Can a Computer Predict BatChat's Favorites?](https://www.kaggle.com/code/danofer/batchat-s-favorite-batman-stories)

## Publishing

```bash
make notebooks   # execute all three locally against data/kaggle
make share       # stage data/kaggle/ + dataset-metadata.json
kaggle datasets version -p data/kaggle -m "message" --dir-mode skip
```

Each notebook is pushed as-is to its kernel (`kaggle kernels push`), with the dataset attached as its only source. Kaggle caps keywords at five.

## Sources and illustration

Sources retain their own terms; redistribution rights for the combined bundle are unresolved, so the Kaggle license is `other`. See [the source notes](enrichment_research.md). The EDA includes one attributed 250×385 *Ego* thumbnail beside commentary on its composition.
