import json

from scripts.package import stage_kaggle


def test_stage_kaggle_copies_tables_flat_and_writes_metadata(tmp_path):
    root = tmp_path / "root"
    (root / "data/processed").mkdir(parents=True)
    (root / "data/processed/stories.csv").write_text("story_id\na\n")
    (root / "references").mkdir()
    (root / "references/kaggle-dataset-about.md").write_text("About")
    (root / "references/kaggle-table-metadata.json").write_text(
        json.dumps({"resources": [{"path": "stories.csv", "source": "data/processed/stories.csv"}]})
    )
    target = tmp_path / "kaggle"
    stage_kaggle(root, target)
    metadata = json.loads((target / "dataset-metadata.json").read_text())
    assert (target / "stories.csv").read_text() == "story_id\na\n"
    assert metadata["description"] == "About" and len(metadata["keywords"]) <= 5
