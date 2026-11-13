"""The bundled, trimmed schema.org vocabulary: types, properties and enumeration members."""

from __future__ import annotations

import difflib
import json
from functools import lru_cache
from importlib import resources

SCHEMA_PREFIXES = (
    "https://schema.org/",
    "http://schema.org/",
    "https://www.schema.org/",
    "http://www.schema.org/",
    "schema:",
)


def local_name(value: str) -> str:
    """``https://schema.org/Product`` or ``schema:Product`` to ``Product``. Other strings are returned unchanged."""
    v = value.strip()
    for prefix in SCHEMA_PREFIXES:
        if v.lower().startswith(prefix):
            return v[len(prefix) :]
    return v


def is_schema_iri(value: str) -> bool:
    return value.strip().lower().startswith(SCHEMA_PREFIXES[:4])


class Vocabulary:
    def __init__(self, data: dict) -> None:
        self.version: str = data["version"]
        self.types: dict[str, list[str]] = data["types"]
        self.data_types: set[str] = set(data["dataTypes"])
        self.properties: dict[str, dict] = data["properties"]
        self.members: dict[str, list[str]] = data["members"]
        self._lower_types = {t.lower(): t for t in self.types}
        self._lower_props = {p.lower(): p for p in self.properties}
        self._lower_members = {m.lower(): m for m in self.members}
        self._ancestors: dict[str, frozenset[str]] = {}
        self._props_of: dict[str, frozenset[str]] = {}

    # Types ---------------------------------------------------------------------------------------------------------

    def is_type(self, name: str) -> bool:
        return name in self.types

    def ancestors(self, name: str) -> frozenset[str]:
        """The type itself and all its super types."""
        cached = self._ancestors.get(name)
        if cached is not None:
            return cached
        seen: set[str] = set()
        stack = [name]
        while stack:
            t = stack.pop()
            if t in seen:
                continue
            seen.add(t)
            stack.extend(self.types.get(t, []))
        result = frozenset(seen)
        self._ancestors[name] = result
        return result

    def is_subtype(self, name: str, *parents: str) -> bool:
        anc = self.ancestors(name)
        return any(p in anc for p in parents)

    def suggest_type(self, name: str) -> str | None:
        exact = self._lower_types.get(name.lower())
        if exact:
            return exact
        match = difflib.get_close_matches(name, list(self.types), n=1, cutoff=0.8)
        return match[0] if match else None

    # Properties ----------------------------------------------------------------------------------------------------

    def is_property(self, name: str) -> bool:
        return name in self.properties

    def properties_of(self, type_name: str) -> frozenset[str]:
        """Properties whose domain includes the type or one of its super types."""
        cached = self._props_of.get(type_name)
        if cached is not None:
            return cached
        anc = self.ancestors(type_name)
        result = frozenset(p for p, info in self.properties.items() if anc.intersection(info["domains"]))
        self._props_of[type_name] = result
        return result

    def expects(self, type_names: list[str], prop: str) -> bool:
        """True when the property is defined for at least one of the types (or the types are unknown)."""
        known = [t for t in type_names if t in self.types]
        if not known:
            return True
        info = self.properties.get(prop)
        if info is None:
            return False
        if not info["domains"]:
            return True
        return any(prop in self.properties_of(t) for t in known)

    def superseded_by(self, prop: str) -> str | None:
        info = self.properties.get(prop)
        return info.get("supersededBy") if info else None

    def ranges(self, prop: str) -> list[str]:
        info = self.properties.get(prop)
        return info["ranges"] if info else []

    def suggest_property(self, name: str, type_names: list[str] | None = None) -> str | None:
        exact = self._lower_props.get(name.lower())
        if exact and exact != name:
            return exact
        pool: list[str] = []
        for t in type_names or []:
            if t in self.types:
                pool.extend(self.properties_of(t))
        candidates = pool or list(self.properties)
        match = difflib.get_close_matches(name, candidates, n=1, cutoff=0.8)
        if not match and pool:
            match = difflib.get_close_matches(name, list(self.properties), n=1, cutoff=0.85)
        return match[0] if match else None

    # Enumerations --------------------------------------------------------------------------------------------------

    def enum_of(self, member: str) -> list[str]:
        return self.members.get(member, [])

    def members_of(self, enum: str) -> list[str]:
        return sorted(m for m, enums in self.members.items() if any(self.is_subtype(e, enum) for e in enums))

    def suggest_member(self, value: str, enum: str) -> str | None:
        options = self.members_of(enum)
        lowered = {o.lower(): o for o in options}
        compact = value.replace(" ", "").replace("_", "").lower()
        if compact in lowered:
            return lowered[compact]
        match = difflib.get_close_matches(value.replace(" ", ""), options, n=1, cutoff=0.7)
        return match[0] if match else None


@lru_cache(maxsize=1)
def get_vocabulary() -> Vocabulary:
    raw = resources.files("rich_results_lint").joinpath("data/schemaorg.json").read_text(encoding="utf-8")
    return Vocabulary(json.loads(raw))
