.PHONY: data offline enrich ratings creators texts notebooks share check

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

notebooks:
	uv run python scripts/execute_notebooks.py

share:
	uv run python -m scripts.package

check:
	uv run python -m pytest -q
	uv run ruff check scripts tests notebooks
	uv run ruff format --check scripts tests notebooks
