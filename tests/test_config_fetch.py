from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from rich_results_lint import FetchError, fetch
from rich_results_lint.config import ConfigError, find_config, load_config


def test_find_config_prefers_dedicated_file(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.other]\nx = 1\n")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert find_config(sub) is None or find_config(sub).parent != tmp_path
    (tmp_path / ".rich-results-lint.toml").write_text('ignore = ["content"]\n')
    assert find_config(sub) == tmp_path / ".rich-results-lint.toml"
    assert load_config(tmp_path / ".rich-results-lint.toml") == {"ignore": ["content"]}


def test_pyproject_section(tmp_path: Path) -> None:
    p = tmp_path / "pyproject.toml"
    p.write_text('[tool.rich-results-lint]\nselect = ["google"]\nfeatures = ["product"]\n')
    assert find_config(tmp_path) == p
    assert load_config(p) == {"select": ["google"], "features": ["product"]}


@pytest.mark.parametrize("body", ['select = "google"', 'severity = "error"', "features = [1]"])
def test_config_validation(tmp_path: Path, body: str) -> None:
    p = tmp_path / ".rich-results-lint.toml"
    p.write_text(body + "\n")
    with pytest.raises(ConfigError):
        load_config(p)


def test_fetch_decodes_charset_and_limits_size() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/big":
            return httpx.Response(200, content=b"x" * 2048, headers={"content-type": "text/html"})
        return httpx.Response(
            200, content="<p>ঢাকা</p>".encode("utf-16"), headers={"content-type": "text/html; charset=utf-16"}
        )

    transport = httpx.MockTransport(handler)
    page = fetch("https://e.com/", transport=transport)
    assert "ঢাকা" in page.text and page.status == 200 and page.content_type == "text/html"
    with pytest.raises(FetchError, match="larger"):
        fetch("https://e.com/big", transport=transport, max_bytes=1024)


def test_fetch_follows_redirects_and_reports_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/a":
            return httpx.Response(302, headers={"location": "/b"})
        if request.url.path == "/b":
            return httpx.Response(200, text="ok", headers={"content-type": "text/html"})
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    assert fetch("https://e.com/a", transport=transport).final_url == "https://e.com/b"
    with pytest.raises(FetchError, match="HTTP 500"):
        fetch("https://e.com/c", transport=transport)
