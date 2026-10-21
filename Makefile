.PHONY: data offline enrich ratings creators texts analyze insights compare notebooks html share check

# Bound native math threads; small folds otherwise spend time oversubscribing CPUs.
export OMP_NUM_THREADS = 2
export OPENBLAS_NUM_THREADS = 2
export MPLCONFIGDIR = /tmp/batchat-mpl
export JUPYTER_RUNTIME_DIR = /tmp/batchat-jupyter

data:
	uv run python scripts/dataset.py

offline:
	uv run python scripts/dataset.py --offline

enrich:
	uv run python scripts/dataset.py --offline --base-only
	uv run python -m scripts.enrich --offline
	uv run python -m scripts.awards --offline
	uv run python -m scripts.catalogue
	uv run python -m scripts.ratings --offline
	uv run python scripts/dataset.py --offline
	uv run python -m scripts.creators --offline
	uv run python -m scripts.texts
	uv run python scripts/dataset.py --offline

ratings:
	uv run python -m scripts.ratings
	uv run python scripts/dataset.py --offline

creators:
	uv run python -m scripts.creators --offline
	uv run python scripts/dataset.py --offline

texts:
	uv run python -m scripts.texts
	uv run python scripts/dataset.py --offline

analyze:
	uv run python -c 'import nbformat; from nbclient import NotebookClient; p="notebooks/1.0-batchat-rankings.ipynb"; n=nbformat.read(p, as_version=4); NotebookClient(n, timeout=900, resources={"metadata":{"path":"."}}).execute(); nbformat.write(n,p)'

insights:
	uv run python -c 'import nbformat; from nbclient import NotebookClient; p="notebooks/2.0-batchat-the-art-of-gotham.ipynb"; n=nbformat.read(p, as_version=4); NotebookClient(n, timeout=900, resources={"metadata":{"path":"."}}).execute(); nbformat.write(n,p)'

compare:
	uv run python -c 'import nbformat; from nbclient import NotebookClient; p="notebooks/3.0-batchat-versus-the-crowd.ipynb"; n=nbformat.read(p, as_version=4); NotebookClient(n, timeout=900, resources={"metadata":{"path":"."}}).execute(); nbformat.write(n,p)'

notebooks: analyze insights compare

html:
	uv run python -m scripts.render

share: html
	uv run python -m scripts.package

check:
	uv run python -m pytest -q
	uv run ruff check scripts tests
	uv run ruff format --check scripts tests
