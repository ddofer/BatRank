import json

from scripts.package import KAGGLE_FILES, stage_kaggle


def test_stage_kaggle_flattens_tables_and_writes_metadata(tmp_path):
    root = tmp_path / "root"
    for name in KAGGLE_FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("story_id\na\n")
    (root / "references/kaggle-dataset-about.md").write_text("About")
    (root / "references/kaggle-table-metadata.json").write_text(
        json.dumps({"resources": [{"path": name.split("/")[-1]} for name in KAGGLE_FILES]})
    )
    target = tmp_path / "kaggle"
    stage_kaggle(root, target)
    metadata = json.loads((target / "dataset-metadata.json").read_text())
    assert sorted(p.name for p in target.glob("*.csv")) == sorted(
        n.split("/")[-1] for n in KAGGLE_FILES
    )
    assert metadata["description"] == "About" and len(metadata["keywords"]) <= 5
