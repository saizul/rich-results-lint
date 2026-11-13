"""Build the trimmed schema.org vocabulary bundled with rich-results-lint.

Usage::

    curl -sSLo schemaorg-current-https.jsonld https://schema.org/version/latest/schemaorg-current-https.jsonld
    python scripts/build_vocab.py schemaorg-current-https.jsonld 30.1

The output, ``src/rich_results_lint/data/schemaorg.json``, keeps only what the linter needs: every type with its
parent types, every property with its domain and range types and its replacement if it was superseded, and every
enumeration member with its enumeration. Labels, comments, external mappings and the country-specific nonprofit
status enumerations are dropped.

schema.org is licensed under CC BY-SA 3.0; see NOTICE.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "src" / "rich_results_lint" / "data" / "schemaorg.json"


def _ids(value: object) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    out = []
    for item in items:
        ref = item.get("@id") if isinstance(item, dict) else item
        if isinstance(ref, str) and ref.startswith("schema:"):
            out.append(ref[len("schema:") :])
    return out


def _types(node: dict) -> list[str]:
    t = node.get("@type")
    return t if isinstance(t, list) else [t]


def build(source: Path, version: str) -> dict:
    graph = json.loads(source.read_text(encoding="utf-8"))["@graph"]
    types: dict[str, list[str]] = {}
    properties: dict[str, dict] = {}
    members: dict[str, list[str]] = {}
    datatypes: set[str] = set()

    for node in graph:
        node_id = node.get("@id", "")
        if not node_id.startswith("schema:"):
            continue
        name = node_id[len("schema:") :]
        kinds = _types(node)
        if "rdfs:Class" in kinds:
            types[name] = sorted(_ids(node.get("rdfs:subClassOf")))
            if "schema:DataType" in kinds:
                datatypes.add(name)
        if "rdf:Property" in kinds:
            prop = {
                "domains": sorted(_ids(node.get("schema:domainIncludes"))),
                "ranges": sorted(_ids(node.get("schema:rangeIncludes"))),
            }
            superseded = _ids(node.get("schema:supersededBy"))
            if superseded:
                prop["supersededBy"] = superseded[0]
            properties[name] = prop
        enum_types = [k[len("schema:") :] for k in kinds if isinstance(k, str) and k.startswith("schema:")]
        if enum_types and "rdfs:Class" not in kinds:
            members[name] = sorted(enum_types)

    # Country-specific nonprofit status codes (NonprofitType and its subtypes) are not used by any rich result.
    def _under(name: str, root: str) -> bool:
        seen, stack = set(), [name]
        while stack:
            t = stack.pop()
            if t == root:
                return True
            if t not in seen:
                seen.add(t)
                stack.extend(types.get(t, []))
        return False

    members = {m: enums for m, enums in members.items() if not any(_under(e, "NonprofitType") for e in enums)}

    # DataType subclasses (Text, URL, Number, Integer, Date ...) are data types too.
    changed = True
    while changed:
        changed = False
        for name, parents in types.items():
            if name not in datatypes and any(p in datatypes for p in parents):
                datatypes.add(name)
                changed = True

    return {
        "version": version,
        "source": "https://schema.org/version/latest/schemaorg-current-https.jsonld",
        "license": "CC BY-SA 3.0, https://creativecommons.org/licenses/by-sa/3.0/",
        "types": dict(sorted(types.items())),
        "dataTypes": sorted(datatypes),
        "properties": dict(sorted(properties.items())),
        "members": dict(sorted(members.items())),
    }


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    vocab = build(Path(argv[0]), argv[1])
    OUT.write_text(json.dumps(vocab, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"wrote {OUT.name}: {len(vocab['types'])} types, {len(vocab['properties'])} properties, "
        f"{len(vocab['members'])} enumeration members"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
