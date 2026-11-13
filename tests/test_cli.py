from __future__ import annotations

import io
import json
from pathlib import Path

import httpx
import pytest

from rich_results_lint.cli import main

from .conftest import FIXTURES

VALID = str(FIXTURES / "valid" / "product.html")
INVALID = str(FIXTURES / "invalid" / "values.html")


def run(*args: str, stdin: str = "", transport: httpx.BaseTransport | None = None) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = main(["--no-config", *args], stdout=out, stderr=err, stdin=io.StringIO(stdin), transport=transport)
    return code, out.getvalue(), err.getvalue()


def test_valid_file_exits_zero() -> None:
    code, out, _ = run(VALID)
    assert code == 0
    assert out.startswith("0 errors")


def test_invalid_file_exits_one() -> None:
    code, out, _ = run(INVALID)
    assert code == 1
    assert "value/date" in out


@pytest.mark.parametrize(("fail_on", "code"), [("error", 1), ("warning", 1), ("info", 1), ("never", 0)])
def test_fail_on(fail_on: str, code: int) -> None:
    assert run(INVALID, "--fail-on", fail_on)[0] == code


def test_fail_on_warning_with_only_warnings() -> None:
    faq = str(FIXTURES / "valid" / "faq.html")
    assert run(faq)[0] == 0
    assert run(faq, "--fail-on", "warning")[0] == 1


def test_json_and_sarif_formats(tmp_path: Path) -> None:
    _, out, _ = run(INVALID, "-f", "json")
    assert json.loads(out)["summary"]["errors"] > 0
    target = tmp_path / "report.sarif"
    _, out, _ = run(INVALID, "--format", "sarif", "-o", str(target))
    assert out == ""
    assert json.loads(target.read_text())["version"] == "2.1.0"


def test_directory_input() -> None:
    _, out, _ = run(str(FIXTURES / "valid"), "-f", "json")
    data = json.loads(out)
    assert data["summary"]["documents"] == len(list((FIXTURES / "valid").glob("*.html")))


def test_select_ignore_and_severity() -> None:
    _, out, _ = run(INVALID, "-f", "json", "--select", "value/date,value/duration")
    found = {f["rule"] for d in json.loads(out)["documents"] for f in d["findings"]}
    assert found == {"value/date", "value/duration"}
    _, out, _ = run(INVALID, "-f", "json", "--ignore", "value", "--ignore", "schema/*")
    found = {f["rule"] for d in json.loads(out)["documents"] for f in d["findings"]}
    assert not any(r.startswith(("value/", "schema/")) for r in found)
    code, _, _ = run(INVALID, "--select", "value/date", "--severity", "value/date=info")
    assert code == 0


def test_feature_option() -> None:
    _, out, _ = run(str(FIXTURES / "invalid" / "job-posting.html"), "-f", "json", "--feature", "recipe")
    found = {f["rule"] for d in json.loads(out)["documents"] for f in d["findings"]}
    assert not any(r.startswith("job/") for r in found)


def test_stdin_html_and_jsonld() -> None:
    html = Path(INVALID).read_text()
    code, out, _ = run("-", stdin=html)
    assert code == 1 and "<stdin>" in out
    code, out, _ = run("-", "-f", "json", stdin='{"@context": "https://schema.org", "@type": "Product", "name": "P"}')
    assert json.loads(out)["documents"][0]["items"][0]["types"] == ["Product"]


def test_jsonld_file(tmp_path: Path) -> None:
    f = tmp_path / "data.jsonld"
    f.write_text('{"@context": "https://schema.org", "@type": "BreadcrumbList"}')
    code, out, _ = run(str(f))
    assert code == 1 and "itemListElement" in out


def test_url_input_with_mock_transport() -> None:
    html = Path(VALID).read_text()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"].startswith("rich-results-lint/")
        if request.url.path == "/moved":
            return httpx.Response(301, headers={"location": "https://shop.example/product"})
        return httpx.Response(200, text=html, headers={"content-type": "text/html; charset=utf-8"})

    code, out, _ = run("https://shop.example/moved", "-f", "json", transport=httpx.MockTransport(handler))
    data = json.loads(out)
    assert code == 0
    assert data["documents"][0]["url"] == "https://shop.example/product"


def test_url_errors_exit_two() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/404":
            return httpx.Response(404)
        if request.url.path == "/pdf":
            return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
        raise httpx.ConnectError("refused", request=request)

    transport = httpx.MockTransport(handler)
    for path, text in (("/404", "HTTP 404"), ("/pdf", "unsupported content type"), ("/down", "ConnectError")):
        code, out, _ = run(f"https://shop.example{path}", transport=transport)
        assert code == 2
        assert "syntax/fetch-failed" in out and text in out


def test_missing_file_exits_two() -> None:
    code, out, _ = run("does-not-exist.html")
    assert code == 2 and "cannot read" in out


def test_usage_errors() -> None:
    assert run()[0] == 2
    assert run(VALID, "--severity", "nonsense")[0] == 2
    assert run(VALID, "--severity", "value/date=fatal")[0] == 2
    assert run(VALID, "--feature", "nope")[0] == 2
    with pytest.raises(SystemExit):
        run("--format", "xml", VALID)


def test_list_rules_and_features() -> None:
    code, out, _ = run("--list-rules")
    assert code == 0 and "google/required" in out and "value/date" in out
    code, out, _ = run("--list-features")
    assert code == 0 and "product" in out and "job-posting" in out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "rich-results-lint" in capsys.readouterr().out


def test_config_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[tool.rich-results-lint]\nignore = ["value"]\nformat = "json"\nfail-on = "never"\n'
        '[tool.rich-results-lint.severity]\n"schema/*" = "info"\n'
    )
    monkeypatch.chdir(tmp_path)
    out, err = io.StringIO(), io.StringIO()
    code = main([INVALID], stdout=out, stderr=err)
    assert code == 0
    data = json.loads(out.getvalue())
    findings = [f for d in data["documents"] for f in d["findings"]]
    assert not any(f["rule"].startswith("value/") for f in findings)
    assert all(f["severity"] == "info" for f in findings if f["rule"].startswith("schema/"))


def test_bad_config(tmp_path: Path) -> None:
    cfg = tmp_path / ".rich-results-lint.toml"
    cfg.write_text('selekt = ["x"]\n')
    out, err = io.StringIO(), io.StringIO()
    assert main(["--config", str(cfg), VALID], stdout=out, stderr=err) == 2
    assert "unknown option" in err.getvalue()
    cfg.write_text("not toml = = =")
    assert main(["--config", str(cfg), VALID], stdout=out, stderr=err) == 2


def test_module_entry_point() -> None:
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "rich_results_lint", "--no-config", VALID], capture_output=True, text=True
    )
    assert result.returncode == 0
