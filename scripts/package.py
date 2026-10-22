"""Stage the flat Kaggle dataset folder: final tables plus dataset-metadata.json."""

import csv
import json
import shutil
from pathlib import Path


def stage_kaggle(root, target):
    """Copy each table named in references/kaggle-table-metadata.json flat into target."""
    tables = json.loads((root / "references/kaggle-table-metadata.json").read_text())
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True)
    for table in tables["resources"]:
        source = root / table["source"]
        destination = target / table["path"]
        if table["path"] in {"stories.csv", "story_features.csv"} and "schema" in table:
            fields = [field["name"] for field in table["schema"]["fields"]]
            with source.open(newline="") as src, destination.open("w", newline="") as dest:
                reader = csv.DictReader(src)
                if not set(fields).issubset(reader.fieldnames or []):
                    raise ValueError(f"Missing columns in {source}")
                writer = csv.DictWriter(dest, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(reader)
        else:
            shutil.copy2(source, destination)
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
