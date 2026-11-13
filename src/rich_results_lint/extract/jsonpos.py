"""A strict JSON parser that remembers the line of every object and key.

The standard :mod:`json` module does not report positions of parsed values. Findings are much easier to act on with
a line number, so JSON-LD is parsed twice: first with :func:`json.loads` (for its error messages), then with this
parser, which returns plain Python values where every object is a :class:`PosDict` carrying line information.
"""

from __future__ import annotations

import json
import re

_NUMBER = re.compile(r"-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?")
_WS = re.compile(r"[ \t\n\r]*")


class PosDict(dict):
    """A dict with the line of its opening brace and of each key."""

    line: int
    key_lines: dict[str, int]


class _Parser:
    def __init__(self, text: str, first_line: int) -> None:
        self.s = text
        self.i = 0
        self.first_line = first_line
        # Line start offsets, for converting positions to lines.
        self._newlines = [m.start() for m in re.finditer("\n", text)]

    def line_at(self, pos: int) -> int:
        lo, hi = 0, len(self._newlines)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._newlines[mid] < pos:
                lo = mid + 1
            else:
                hi = mid
        return self.first_line + lo

    def ws(self) -> None:
        self.i = _WS.match(self.s, self.i).end()  # type: ignore[union-attr]

    def value(self):
        self.ws()
        ch = self.s[self.i : self.i + 1]
        if ch == "{":
            return self.obj()
        if ch == "[":
            return self.arr()
        if ch == '"':
            return self.string()
        for word, val in (("true", True), ("false", False), ("null", None)):
            if self.s.startswith(word, self.i):
                self.i += len(word)
                return val
        m = _NUMBER.match(self.s, self.i)
        if m and m.end() > self.i:
            self.i = m.end()
            text = m.group(0)
            return float(text) if any(c in text for c in ".eE") else int(text)
        raise ValueError(f"unexpected character at offset {self.i}")

    def obj(self) -> PosDict:
        out = PosDict()
        out.line = self.line_at(self.i)
        out.key_lines = {}
        self.i += 1
        self.ws()
        if self.s.startswith("}", self.i):
            self.i += 1
            return out
        while True:
            self.ws()
            key_line = self.line_at(self.i)
            key = self.string()
            self.ws()
            if not self.s.startswith(":", self.i):
                raise ValueError("expected ':'")
            self.i += 1
            out[key] = self.value()
            out.key_lines.setdefault(key, key_line)
            self.ws()
            if self.s.startswith(",", self.i):
                self.i += 1
                continue
            if self.s.startswith("}", self.i):
                self.i += 1
                return out
            raise ValueError("expected ',' or '}'")

    def arr(self) -> list:
        out: list = []
        self.i += 1
        self.ws()
        if self.s.startswith("]", self.i):
            self.i += 1
            return out
        while True:
            out.append(self.value())
            self.ws()
            if self.s.startswith(",", self.i):
                self.i += 1
                continue
            if self.s.startswith("]", self.i):
                self.i += 1
                return out
            raise ValueError("expected ',' or ']'")

    def string(self) -> str:
        if not self.s.startswith('"', self.i):
            raise ValueError("expected string")
        decoder = json.JSONDecoder()
        value, end = decoder.raw_decode(self.s, self.i)
        self.i = end
        return value


def loads_with_lines(text: str, first_line: int = 1):
    """Parse JSON text. Raises :class:`json.JSONDecodeError` for invalid JSON (from the standard parser)."""
    json.loads(text)  # Standard error messages and positions for invalid input.
    parser = _Parser(text, first_line)
    value = parser.value()
    return value
