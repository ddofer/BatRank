from zipfile import ZipFile

from scripts.package import write_bundle


def test_bundle_preserves_layout_and_replaces_old_archive(tmp_path):
    source = tmp_path / "data/processed/stories.csv"
    source.parent.mkdir(parents=True)
    source.write_text("story_id,rank\na,1\n")
    target = tmp_path / "release.zip"
    target.write_text("obsolete archive")
    write_bundle(target, [source, source], tmp_path)
    with ZipFile(target) as bundle:
        assert bundle.namelist() == ["data/processed/stories.csv"]
        assert bundle.read(bundle.namelist()[0]) == source.read_bytes()
    assert not target.with_suffix(".tmp").exists()
