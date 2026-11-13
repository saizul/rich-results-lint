from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "build_vocab.py"


def _module():
    spec = importlib.util.spec_from_file_location("build_vocab", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_vocab_from_a_small_release(tmp_path: Path) -> None:
    release = {
        "@graph": [
            {"@id": "schema:Thing", "@type": "rdfs:Class"},
            {"@id": "schema:DataType", "@type": "rdfs:Class"},
            {"@id": "schema:Text", "@type": ["schema:DataType", "rdfs:Class"]},
            {"@id": "schema:URL", "@type": "rdfs:Class", "rdfs:subClassOf": {"@id": "schema:Text"}},
            {"@id": "schema:Enumeration", "@type": "rdfs:Class", "rdfs:subClassOf": {"@id": "schema:Thing"}},
            {"@id": "schema:Color", "@type": "rdfs:Class", "rdfs:subClassOf": {"@id": "schema:Enumeration"}},
            {"@id": "schema:Red", "@type": "schema:Color"},
            {
                "@id": "schema:name",
                "@type": "rdf:Property",
                "schema:domainIncludes": {"@id": "schema:Thing"},
                "schema:rangeIncludes": [{"@id": "schema:Text"}],
            },
            {"@id": "schema:oldName", "@type": "rdf:Property", "schema:supersededBy": {"@id": "schema:name"}},
            {"@id": "ext:Other", "@type": "rdfs:Class"},
        ]
    }
    source = tmp_path / "release.jsonld"
    source.write_text(json.dumps(release))
    vocab = _module().build(source, "1.0")
    assert vocab["version"] == "1.0"
    assert vocab["types"]["Color"] == ["Enumeration"]
    assert "Other" not in vocab["types"]
    assert set(vocab["dataTypes"]) == {"Text", "URL"}
    assert vocab["properties"]["name"] == {"domains": ["Thing"], "ranges": ["Text"]}
    assert vocab["properties"]["oldName"]["supersededBy"] == "name"
    assert vocab["members"] == {"Red": ["Color"]}


def test_bundled_vocabulary_metadata() -> None:
    data = json.loads((SCRIPT.parent.parent / "src" / "rich_results_lint" / "data" / "schemaorg.json").read_text())
    assert data["version"] == "30.1"
    assert "CC BY-SA" in data["license"]
