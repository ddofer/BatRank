"""Build the two sharing bundles from the current data and executed notebooks."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def write_bundle(target, files, root):
    temporary = target.with_suffix(".tmp")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as bundle:
        for source in sorted(set(files)):
            bundle.write(source, source.relative_to(root))
    with ZipFile(temporary) as bundle:
        assert bundle.testzip() is None
        for name in bundle.namelist():
            assert bundle.read(name) == (root / name).read_bytes(), name
    temporary.replace(target)
    print(f"{target.name}: {target.stat().st_size / 1024**2:.2f} MiB")


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    reports = root / "reports"
    validation = set(reports.glob("*validation.json"))
    dataset = [
        root / "README.md",
        root / "data/external/creator_watch.csv",
        root / "data/external/animal_watch.csv",
        root / "data/external/story_labels.csv",
    ]
    dataset += list((root / "data/processed").glob("*.csv"))
    dataset += [p for p in (root / "references").iterdir() if p.suffix in {".md", ".csv", ".json"}]
    dataset += [
        *validation,
        reports / "review.md",
        reports / "hatter_credit_audit.csv",
        root / "scripts/analysis.py",
    ]
    notebooks = [root / p for p in ["README.md", "Makefile", "pyproject.toml", "uv.lock"]]
    notebooks += [root / "references/kaggle-notebook-copy.md"]
    for folder, pattern in [
        ("notebooks", "*.ipynb"),
        ("reports/notebooks", "*.html"),
        ("scripts", "*.py"),
        ("tests", "*.py"),
        ("reports", "*.csv"),
        ("reports/figures", "*.png"),
    ]:
        notebooks += list((root / folder).glob(pattern))
    notebooks += [p for p in reports.glob("*.json") if p not in validation]
    write_bundle(reports / "batchat-dataset.zip", dataset, root)
    write_bundle(reports / "batchat-notebooks.zip", notebooks, root)
