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


def test_story_projection_preserves_values_and_column_order(tmp_path):
    root = tmp_path / "root"
    (root / "data/processed").mkdir(parents=True)
    source = root / "data/processed/stories.csv"
    source.write_text('story_id,title,rank,detail\na,"A, story",1,unknown\n')
    (root / "references").mkdir()
    (root / "references/kaggle-dataset-about.md").write_text("About")
    resources = [
        {
            "path": name,
            "source": "data/processed/stories.csv",
            "schema": {"fields": [{"name": field} for field in fields]},
        }
        for name, fields in [
            ("stories.csv", ["rank", "title", "story_id"]),
            ("story_features.csv", ["story_id", "detail"]),
        ]
    ]
    (root / "references/kaggle-table-metadata.json").write_text(
        json.dumps({"resources": resources})
    )
    target = tmp_path / "kaggle"
    stage_kaggle(root, target)
    assert (target / "stories.csv").read_text() == 'rank,title,story_id\n1,"A, story",a\n'
    assert (target / "story_features.csv").read_text() == "story_id,detail\na,unknown\n"
    assert source.read_text() == 'story_id,title,rank,detail\na,"A, story",1,unknown\n'
