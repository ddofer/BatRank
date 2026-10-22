"""Execute notebooks atomically; failed runs leave the previous notebook intact."""

import os
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/batchat-mpl")
os.environ.setdefault("JUPYTER_RUNTIME_DIR", "/tmp/batchat-jupyter")


def execute(path):
    notebook = nbformat.read(path, as_version=4)
    NotebookClient(notebook, timeout=900, resources={"metadata": {"path": str(ROOT)}}).execute()
    nbformat.validate(notebook)
    temporary = path.with_suffix(".ipynb.tmp")
    try:
        nbformat.write(notebook, temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"{path.name}: executed {len(notebook.cells)} cells", flush=True)


if __name__ == "__main__":
    for path in (
        map(Path, sys.argv[1:])
        if len(sys.argv) > 1
        else sorted((ROOT / "notebooks").glob("*.ipynb"))
    ):
        execute(path)
