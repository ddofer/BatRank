from bs4 import BeautifulSoup

from scripts.render import relocate_links


def test_render_links_follow_notebook_and_document_locations(tmp_path):
    source = tmp_path / "notebooks/one.ipynb"
    destination = tmp_path / "reports/notebooks/one.html"
    html = """<a href="two.ipynb#section">Next</a>
    <a href="../references/data_dictionary.md">Fields</a>
    <a href="#local">Here</a><a href="https://example.org/a">Source</a>
    <img alt="Chart description" src="data:image/png;base64,abc">"""
    soup = BeautifulSoup(relocate_links(html, source, destination), "html.parser")
    assert [a["href"] for a in soup.select("a")] == [
        "two.html#section",
        "../../references/data_dictionary.md",
        "#local",
        "https://example.org/a",
    ]
    assert soup.img["alt"] == "Chart description"
