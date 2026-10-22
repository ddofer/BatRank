"""Stage the flat Kaggle dataset folder: final tables plus dataset-metadata.json."""

import json
import shutil
from pathlib import Path

KAGGLE_FILES = [
    "data/processed/stories.csv",
    "data/processed/issues.csv",
    "data/processed/creators.csv",
    "data/processed/story_creators.csv",
    "data/processed/creator_awards.csv",
    "data/processed/story_texts.csv",
    "references/award_events.csv",
    "data/external/animal_watch.csv",
    "data/external/story_labels.csv",
    "references/hatter_story_roles.csv",
    "data/external/creator_watch.csv",
]


def stage_kaggle(root, target):
    """Copy the final tables flat into target and write Kaggle's dataset-metadata.json."""
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for name in KAGGLE_FILES:
        shutil.copy2(root / name, target / Path(name).name)
    tables = json.loads((root / "references/kaggle-table-metadata.json").read_text())
    assert sorted(r["path"] for r in tables["resources"]) == sorted(
        p.name for p in target.iterdir()
    )
    metadata = {
        "id": "danofer/batchat-batman-rankings",
        "title": "BatRank: A BatChat Batman Ranking Dataset",
        "subtitle": "Creative teams, characters, outside ratings, and 700,000 words of plot summaries",
        "description": (root / "references/kaggle-dataset-about.md").read_text(),
        "licenses": [{"name": "other"}],
        "keywords": [
            "popular culture",
            "comics and animation",
            "data visualization",
            "nlp",
            "movies and tv shows",
        ],
        "resources": tables["resources"],
    }
    (target / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=1, ensure_ascii=False)
    )
    print(f"{target}: {len(KAGGLE_FILES)} tables")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    stage_kaggle(root, root / "data/kaggle")
