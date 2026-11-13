"""Command line interface: ``rich-results-lint [options] SOURCE...``."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

import httpx

from ._version import __version__
from .checks.features import FEATURES
from .config import ConfigError, find_config, load_config
from .fetch import DEFAULT_USER_AGENT, FetchError, fetch
from .linter import Options, lint_file, lint_html, lint_jsonld
from .model import Document, Finding, Severity
from .report import FORMATS, render_text
from .rules import RULES

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

HTML_SUFFIXES = {".html", ".htm", ".xhtml", ".json", ".jsonld"}
FAIL_ON = ("error", "warning", "info", "never")


def _split(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for v in values or []:
        out.extend(x.strip() for x in v.split(",") if x.strip())
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rich-results-lint",
        description="Lint JSON-LD, Microdata and RDFa structured data against schema.org and Google's rich result "
        "requirements.",
        epilog="Exit status: 0 no findings at or above --fail-on, 1 findings, 2 usage, config or input error.",
    )
    p.add_argument(
        "sources", nargs="*", metavar="SOURCE", help="HTML or JSON-LD file, directory, http(s) URL, or - for stdin"
    )
    p.add_argument("-f", "--format", choices=sorted(FORMATS), help="output format (default: text)")
    p.add_argument("-o", "--output", help="write the report to a file instead of standard output")
    p.add_argument("--fail-on", choices=FAIL_ON, help="lowest severity that makes the exit status 1 (default: error)")
    p.add_argument(
        "--select",
        action="append",
        metavar="RULES",
        help="only report these rules (comma-separated ids, groups or globs)",
    )
    p.add_argument("--ignore", action="append", metavar="RULES", help="do not report these rules")
    p.add_argument(
        "--severity",
        action="append",
        metavar="RULE=LEVEL",
        help="change a rule's severity, e.g. merchant/required=error",
    )
    p.add_argument(
        "--feature", action="append", metavar="ID", help="only run these Google feature checks (see --list-features)"
    )
    p.add_argument("--no-content-checks", action="store_true", help="skip the visible-content hints")
    p.add_argument("--base-url", help="page URL of local files, used for relative URL messages and video checks")
    p.add_argument("--timeout", type=float, help="HTTP timeout in seconds (default: 20)")
    p.add_argument("--user-agent", help="HTTP User-Agent header")
    p.add_argument("--config", help="config file (default: nearest .rich-results-lint.toml or pyproject.toml)")
    p.add_argument("--no-config", action="store_true", help="ignore config files")
    p.add_argument("--color", choices=("auto", "always", "never"), default="auto", help="colour text output")
    p.add_argument("-v", "--verbose", action="store_true", help="list every document, also those without findings")
    p.add_argument("--list-rules", action="store_true", help="print all rules and exit")
    p.add_argument("--list-features", action="store_true", help="print the Google features checked and exit")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _expand(sources: list[str]) -> list[str]:
    out: list[str] = []
    for s in sources:
        path = Path(s)
        if s == "-" or s.lower().startswith(("http://", "https://")) or not path.is_dir():
            out.append(s)
            continue
        out.extend(str(p) for p in sorted(path.rglob("*")) if p.is_file() and p.suffix.lower() in HTML_SUFFIXES)
    return out


def _error_doc(source: str, message: str) -> Document:
    doc = Document(source=source)
    doc.findings.append(Finding("syntax/fetch-failed", Severity.ERROR, message, source=source))
    return doc


def main(
    argv: Sequence[str] | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    stdin: TextIO | None = None,
    transport: httpx.BaseTransport | None = None,
) -> int:
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.list_rules:
        width = max(len(r) for r in RULES)
        for rule in RULES.values():
            out.write(f"{rule.id:<{width}}  {rule.severity.value:<7}  {rule.description}\n")
        return EXIT_OK
    if args.list_features:
        for f in FEATURES:
            types = ", ".join(f.types)
            out.write(f"{f.id:<15} {f.name:<16} {types}\n")
        return EXIT_OK
    if not args.sources:
        parser.print_usage(err)
        err.write("rich-results-lint: error: give at least one SOURCE (file, directory, URL or -)\n")
        return EXIT_ERROR

    try:
        config: dict = {}
        if not args.no_config:
            path = Path(args.config) if args.config else find_config(Path.cwd())
            if path is not None:
                config = load_config(path)
        severity = dict(config.get("severity", {}))
        for pair in args.severity or []:
            if "=" not in pair:
                raise ConfigError(f"--severity expects RULE=LEVEL, got {pair!r}")
            rule, level = pair.split("=", 1)
            severity[rule.strip()] = level.strip()
        options = Options(
            select=_split(args.select) or list(config.get("select", [])),
            ignore=_split(args.ignore) + list(config.get("ignore", [])),
            severity=severity,
            features=_split(args.feature) or list(config.get("features", [])),
            content_checks=not args.no_content_checks and bool(config.get("content-checks", True)),
        )
    except (ConfigError, ValueError) as exc:
        err.write(f"rich-results-lint: error: {exc}\n")
        return EXIT_ERROR

    fmt = args.format or config.get("format", "text")
    if fmt not in FORMATS:
        err.write(f"rich-results-lint: error: unknown format {fmt!r}\n")
        return EXIT_ERROR
    fail_on = args.fail_on or config.get("fail-on", "error")
    if fail_on not in FAIL_ON:
        err.write(f"rich-results-lint: error: unknown fail-on level {fail_on!r}\n")
        return EXIT_ERROR
    timeout = args.timeout or float(config.get("timeout", 20.0))
    user_agent = args.user_agent or config.get("user-agent", DEFAULT_USER_AGENT)
    base_url = args.base_url or config.get("base-url")

    docs: list[Document] = []
    input_error = False
    sources = _expand(args.sources)
    if not sources:
        err.write("rich-results-lint: error: no HTML or JSON-LD files found\n")
        return EXIT_ERROR
    for source in sources:
        if source == "-":
            text = (stdin or sys.stdin).read()
            lint = lint_jsonld if text.lstrip().startswith(("{", "[")) else lint_html
            docs.append(lint(text, source="<stdin>", url=base_url, options=options))
        elif source.lower().startswith(("http://", "https://")):
            try:
                page = fetch(source, timeout=timeout, user_agent=user_agent, transport=transport)
            except FetchError as exc:
                docs.append(_error_doc(source, str(exc)))
                input_error = True
                continue
            lint = lint_jsonld if page.content_type in ("application/ld+json", "application/json") else lint_html
            docs.append(lint(page.text, source=source, url=page.final_url, options=options))
        else:
            try:
                docs.append(lint_file(source, options=options, url=base_url))
            except OSError as exc:
                docs.append(_error_doc(source, f"cannot read {source}: {exc.strerror or exc}"))
                input_error = True

    if fmt == "text":
        color = args.color == "always" or (
            args.color == "auto"
            and not args.output
            and hasattr(out, "isatty")
            and out.isatty()
            and "NO_COLOR" not in os.environ
        )
        report = render_text(docs, color=color, verbose=args.verbose)
    else:
        report = FORMATS[fmt](docs)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
    else:
        out.write(report)

    if input_error:
        return EXIT_ERROR
    if fail_on == "never":
        return EXIT_OK
    threshold = Severity(fail_on).rank
    failing = any(f.severity.rank >= threshold for d in docs for f in d.findings)
    return EXIT_FINDINGS if failing else EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
