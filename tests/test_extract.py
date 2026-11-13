from __future__ import annotations

import json

import pytest

from rich_results_lint.extract import parse_html, visible_text
from rich_results_lint.extract.jsonld import extract_from_dom, parse_jsonld
from rich_results_lint.extract.jsonpos import loads_with_lines
from rich_results_lint.extract.microdata import extract_microdata
from rich_results_lint.extract.rdfa import extract_rdfa
from rich_results_lint.model import Item, Syntax


class Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int]] = []

    def __call__(self, rule: str, message: str, line: int = 0, path: str = "") -> None:
        self.calls.append((rule, message, line))

    @property
    def rules(self) -> set[str]:
        return {c[0] for c in self.calls}


# JSON with positions --------------------------------------------------------------------------------------------


def test_loads_with_lines_tracks_lines() -> None:
    text = '{\n  "a": 1,\n  "b": {\n    "c": [true, null, "x"]\n  }\n}'
    data = loads_with_lines(text, first_line=10)
    assert data == json.loads(text)
    assert data.line == 10
    assert data.key_lines == {"a": 11, "b": 12}
    assert data["b"].line == 12
    assert data["b"].key_lines["c"] == 13


def test_loads_with_lines_numbers_and_escapes() -> None:
    data = loads_with_lines('{"n": -1.5e3, "i": 42, "s": "a\\"b\\u00e9", "e": [], "o": {}}')
    assert data == {"n": -1500.0, "i": 42, "s": 'a"bé', "e": [], "o": {}}


def test_loads_with_lines_raises_standard_errors() -> None:
    with pytest.raises(json.JSONDecodeError):
        loads_with_lines('{"a": 1,}')


# JSON-LD --------------------------------------------------------------------------------------------------------


def test_jsonld_basic_and_prefixes() -> None:
    rec = Recorder()
    items = parse_jsonld(
        '{"@context": "https://schema.org", "@type": "schema:Product", "https://schema.org/name": "X", '
        '"offers": [{"@type": "Offer", "price": 5}, {"@type": "Offer", "price": {"@value": 6}}]}',
        1,
        "$",
        rec,
    )
    assert len(items) == 1
    product = items[0]
    assert product.types == ["Product"]
    assert product.texts("name") == ["X"]
    assert [o.first("price") for o in product.items("offers")] == [5, 6]
    assert rec.calls == []


def test_jsonld_graph_and_arrays() -> None:
    rec = Recorder()
    items = parse_jsonld(
        '[{"@context": "https://schema.org", "@graph": [{"@type": "Organization", "@id": "#o"}, {"@type": "WebSite"}]},'
        ' {"@context": "https://schema.org", "@type": "Person", "name": "P"}]',
        1,
        "$s",
        rec,
    )
    assert [i.types for i in items] == [["Organization"], ["WebSite"], ["Person"]]
    assert items[0].id == "#o"
    assert items[0].path == "$s[0].@graph[0]"


def test_jsonld_reference_and_lists() -> None:
    items = parse_jsonld(
        '{"@context": "https://schema.org", "@type": "Article", "author": {"@id": "#me"}, '
        '"keywords": {"@list": ["a", "b"]}, "@type2": 1}',
        1,
        "$",
        Recorder(),
    )
    author = items[0].items("author")[0]
    assert author.is_reference and author.id == "#me"
    assert items[0].texts("keywords") == ["a", "b"]


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        ('{"@type": "Thing",}', "syntax/json-invalid"),
        ("", "syntax/empty-script"),
        ('"text"', "syntax/json-ld-shape"),
        ('{"@type": "Thing"}', "syntax/missing-context"),
        ('{"@context": "https://example.org", "@type": "Thing"}', "syntax/unknown-context"),
        ('{"@context": "https://schema.org", "@typ": "Thing"}', "syntax/unknown-keyword"),
    ],
)
def test_jsonld_problems(text: str, rule: str) -> None:
    rec = Recorder()
    parse_jsonld(text, 1, "$", rec)
    assert rule in rec.rules


@pytest.mark.parametrize(
    "context",
    [
        '"https://schema.org"',
        '"http://schema.org/"',
        '"https://schema.org/docs/jsonldcontext.jsonld"',
        '["https://schema.org", {"ex": "https://example.org/"}]',
        '{"@vocab": "https://schema.org/"}',
        '{"schema": "https://schema.org/"}',
    ],
)
def test_jsonld_accepted_contexts(context: str) -> None:
    rec = Recorder()
    parse_jsonld(f'{{"@context": {context}, "@type": "Thing"}}', 1, "$", rec)
    assert "syntax/unknown-context" not in rec.rules


def test_jsonld_error_line_is_page_line() -> None:
    html = '<html>\n<head>\n<script type=\'application/ld+json\'>\n{\n  "a": 1\n  "b": 2\n}\n</script>'
    rec = Recorder()
    extract_from_dom(parse_html(html), rec)
    assert rec.calls[0][0] == "syntax/json-invalid"
    assert rec.calls[0][2] == 6


def test_jsonld_comment_wrappers() -> None:
    html = '<script type="application/ld+json"><!--\n{"@context":"https://schema.org","@type":"Thing"}\n--></script>'
    rec = Recorder()
    items = extract_from_dom(parse_html(html), rec)
    assert items and not rec.calls


def test_jsonld_script_type_variants() -> None:
    html = (
        '<script type="application/ld+json; charset=utf-8">{"@context":"https://schema.org","@type":"A"}</script>'
        '<script type="APPLICATION/LD+JSON">{"@context":"https://schema.org","@type":"B"}</script>'
        '<script type="application/json">{"@type":"C"}</script>'
    )
    items = extract_from_dom(parse_html(html), Recorder())
    assert [i.types for i in items] == [["A"], ["B"]]


def test_jsonld_property_lines() -> None:
    items = parse_jsonld('{\n"@context": "https://schema.org",\n"@type": "Thing",\n"name": "x"\n}', 20, "$", Recorder())
    assert items[0].line == 20
    assert items[0].line_of("name") == 23


# Microdata ------------------------------------------------------------------------------------------------------


MICRODATA = """
<div itemscope itemtype="https://schema.org/Product" itemid="#p" itemref="extra">
  <span itemprop="name">Lamp</span>
  <img itemprop="image" src="/lamp.jpg">
  <a itemprop="url" href="https://example.com/lamp">link</a>
  <meta itemprop="sku" content="L-1">
  <time itemprop="releaseDate" datetime="2026-01-01">January</time>
  <data itemprop="weight" value="2">2 kg</data>
  <div itemprop="offers" itemscope itemtype="https://schema.org/Offer">
    <span itemprop="price" content="10.00">$10</span>
    <div itemscope itemtype="https://schema.org/Thing"><span itemprop="name">Not a property</span></div>
  </div>
</div>
<p id="extra"><span itemprop="color">Red</span></p>
"""


def test_microdata_values() -> None:
    rec = Recorder()
    items = extract_microdata(parse_html(MICRODATA), rec)
    product = items[0]
    assert product.syntax is Syntax.MICRODATA
    assert product.types == ["Product"]
    assert product.id == "#p"
    assert product.texts("name") == ["Lamp"]
    assert product.texts("image") == ["/lamp.jpg"]
    assert product.texts("url") == ["https://example.com/lamp"]
    assert product.texts("sku") == ["L-1"]
    assert product.texts("releaseDate") == ["2026-01-01"]
    assert product.texts("weight") == ["2"]
    assert product.texts("color") == ["Red"]
    offer = product.items("offers")[0]
    assert offer.texts("price") == ["10.00"]
    assert "name" not in offer.properties
    # The unattached Thing inside the offer is a top-level item of its own.
    assert [i.types for i in items] == [["Product"], ["Thing"]]


def test_microdata_multiple_props_and_types() -> None:
    html = (
        '<div itemscope itemtype="https://schema.org/Product https://schema.org/Car">'
        '<span itemprop="name alternateName">X</span></div>'
    )
    item = extract_microdata(parse_html(html), Recorder())[0]
    assert item.types == ["Product", "Car"]
    assert item.texts("name") == ["X"] and item.texts("alternateName") == ["X"]


def test_microdata_itemref_loop_does_not_hang() -> None:
    html = (
        '<div id="a" itemscope itemtype="https://schema.org/Thing" itemref="b"></div>'
        '<div id="b" itemprop="about" itemscope itemref="a"></div>'
    )
    items = extract_microdata(parse_html(html), Recorder())
    assert items


def test_microdata_missing_type() -> None:
    rec = Recorder()
    extract_microdata(parse_html('<div itemscope><span itemprop="name">x</span></div>'), rec)
    assert "syntax/microdata-no-type" in rec.rules


# RDFa -----------------------------------------------------------------------------------------------------------


def test_rdfa_vocab_and_nesting() -> None:
    html = """
    <div vocab="https://schema.org/" typeof="Event">
      <span property="name">Concert</span>
      <time property="startDate" datetime="2030-01-01T19:00">7pm</time>
      <div property="location" typeof="Place"><span property="name">Hall</span>
        <a property="url" href="https://example.com/hall">Hall</a></div>
      <span property="og:title">ignored</span>
    </div>"""
    items = extract_rdfa(parse_html(html), Recorder())
    assert len(items) == 1
    event = items[0]
    assert event.syntax is Syntax.RDFA
    assert event.texts("startDate") == ["2030-01-01T19:00"]
    place = event.items("location")[0]
    assert place.types == ["Place"]
    assert place.texts("name") == ["Hall"]
    assert place.texts("url") == ["https://example.com/hall"]
    assert event.texts("name") == ["Concert"]
    assert "og:title" not in event.properties and "title" not in event.properties


def test_rdfa_prefix() -> None:
    html = (
        '<div prefix="s: https://schema.org/" typeof="s:Product">'
        '<span property="s:name">P</span><span property="name">no vocab</span></div>'
    )
    item = extract_rdfa(parse_html(html), Recorder())[0]
    assert item.types == ["Product"]
    assert item.texts("name") == ["P"]


def test_rdfa_default_schema_prefix_and_missing_vocab() -> None:
    rec = Recorder()
    items = extract_rdfa(
        parse_html('<div typeof="schema:Thing"><span property="schema:name">n</span></div><div typeof="Thing"></div>'),
        rec,
    )
    assert items[0].types == ["Thing"] and items[0].texts("name") == ["n"]
    assert "syntax/rdfa-no-vocab" in rec.rules


# DOM ------------------------------------------------------------------------------------------------------------


def test_dom_recovers_from_broken_markup() -> None:
    root = parse_html("<div><p>One<p>Two</div><span>Three</b></span>")
    assert root.text() == "OneTwoThree"


def test_visible_text_skips_hidden_content() -> None:
    html = """<html><head><title>T</title><style>p{}</style></head><body>
    <h1>Shown</h1><script>var x = "hidden";</script><div hidden>Hidden1</div>
    <div style="display: none">Hidden2</div><noscript>Hidden3</noscript>
    <p aria-hidden="true">Hidden4</p><p>Also shown</p></body></html>"""
    text = visible_text(parse_html(html))
    assert "Shown" in text and "Also shown" in text
    for hidden in ("hidden", "Hidden1", "Hidden2", "Hidden3", "Hidden4", "p{}"):
        assert hidden not in text


def test_item_helpers() -> None:
    item = Item(types=["Thing"], syntax=Syntax.JSON_LD)
    item.add("name", "  ")
    assert not item.has("name")
    item.add("name", "x")
    assert item.has("name") and item.first("name") == "  "
    assert item.label() == "Thing"
    ref = Item(types=[], syntax=Syntax.JSON_LD, id="#a", is_reference=True)
    assert ref.label() == "@id reference"


def test_deeply_nested_html_does_not_crash() -> None:
    from .conftest import lint

    html = (
        "<div>" * 5000
        + '<span itemscope itemtype="https://schema.org/Thing"><b itemprop="name">deep</b></span>'
        + "</div>" * 5000
    )
    doc = lint(html)
    assert doc.items and doc.items[0].types == ["Thing"]


def test_deeply_nested_json_is_reported() -> None:
    rec = Recorder()
    parse_jsonld("[" * 100000 + "]" * 100000, 1, "$", rec)
    assert "syntax/json-invalid" in rec.rules or "syntax/json-ld-shape" in rec.rules
