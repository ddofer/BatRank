"""Render notebooks with local links that still work from reports/notebooks."""

import os
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

import nbformat
from bs4 import BeautifulSoup
from nbconvert import HTMLExporter


def relocate_links(html, source, destination):
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        url = urlsplit(link["href"])
        if url.scheme or url.netloc or not url.path or url.path.startswith("/"):
            continue
        target = (source.parent / unquote(url.path)).resolve()
        if target.suffix == ".ipynb" and target.parent == source.parent.resolve():
            target = destination.parent / target.with_suffix(".html").name
        path = os.path.relpath(target, destination.parent)
        link["href"] = urlunsplit(("", "", path, url.query, url.fragment))
    return str(soup)


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    exporter = HTMLExporter(
        template_name="classic",
        exclude_input=True,
        exclude_input_prompt=True,
        exclude_output_prompt=True,
    )
    for source in sorted((root / "notebooks").glob("*.ipynb")):
        destination = root / "reports/notebooks" / source.with_suffix(".html").name
        destination.parent.mkdir(parents=True, exist_ok=True)
        html, _ = exporter.from_notebook_node(nbformat.read(source, as_version=4))
        destination.write_text(relocate_links(html, source, destination), encoding="utf-8")
        print(destination.relative_to(root))
