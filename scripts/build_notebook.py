"""Build a notebook from its percent-format .py source: build_notebook.py SRC.py DEST.ipynb.

Markdown cells come from `# %% [markdown]` blocks, code cells from `# %%` blocks. An image
referenced as `attachment:NAME` is read from the file NAME next to the source and embedded.
"""

import base64
import mimetypes
import re
import sys
from pathlib import Path

import nbformat


def attachment(path):
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {mime: base64.b64encode(path.read_bytes()).decode()}


def build(src, dest):
    nb = nbformat.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"},
        "language_info": {"name": "python"},
    }
    for chunk in re.split(r"^# %%", src.read_text(), flags=re.M)[1:]:
        head, _, body = chunk.partition("\n")
        body = body.strip("\n")
        if "[markdown]" in head:
            text = "\n".join(
                line[2:] if line.startswith("# ") else line.lstrip("#")
                for line in body.splitlines()
            )
            cell = nbformat.v4.new_markdown_cell(text)
            used = {
                k: attachment(src.parent / k) for k in re.findall(r"attachment:([\w.-]+)", text)
            }
            if used:
                cell["attachments"] = used
        else:
            cell = nbformat.v4.new_code_cell(body)
        nb.cells.append(cell)
    nbformat.validate(nb)
    nbformat.write(nb, dest)
    print(f"{dest}: {len(nb.cells)} cells")


if __name__ == "__main__":
    build(Path(sys.argv[1]), Path(sys.argv[2]))
