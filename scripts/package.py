"""Stage the flat Kaggle dataset folder: final tables plus dataset-metadata.json."""

import json
import shutil
from pathlib import Path


def stage_kaggle(root, target):
    """Copy each table named in references/kaggle-table-metadata.json flat into target."""
    tables = json.loads((root / "references/kaggle-table-metadata.json").read_text())
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for table in tables["resources"]:
        shutil.copy2(root / table["source"], target / table["path"])
    metadata = {
        "id": "danofer/batchat-batman-rankings",
        "title": "BatRank: A BatChat Batman Ranking Dataset",
        "subtitle": "Creative teams, characters, outside ratings, and 700,000 words of plot summaries",
        "description": (root / "references/kaggle-dataset-about.md").read_text(),
        "licenses": [{"name": "other"}],
        "keywords": [
            "popular culture",
            "comics and animation",
            "movies and tv shows",
            "nlp",
            "data visualization",
        ],
        "isPrivate": False,
        "resources": [{k: v for k, v in r.items() if k != "source"} for r in tables["resources"]],
    }
    (target / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=1, ensure_ascii=False)
    )
    print(f"{target}: {len(tables['resources'])} tables")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    stage_kaggle(root, root / "data/kaggle")
