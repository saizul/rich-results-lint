"""Fetch pages over HTTP with httpx."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from ._version import __version__

DEFAULT_USER_AGENT = f"rich-results-lint/{__version__} (+https://github.com/saizul/rich-results-lint)"
MAX_BYTES = 10 * 1024 * 1024


class FetchError(Exception):
    """The page could not be fetched."""


@dataclass
class Page:
    url: str
    final_url: str
    status: int
    content_type: str
    text: str


def fetch(
    url: str,
    *,
    timeout: float = 20.0,
    user_agent: str = DEFAULT_USER_AGENT,
    transport: httpx.BaseTransport | None = None,
    max_bytes: int = MAX_BYTES,
) -> Page:
    """GET a page, following redirects. Raises :class:`FetchError` for network errors, HTTP errors and non-HTML."""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/ld+json;q=0.9,*/*;q=0.5",
    }
    try:
        with (
            httpx.Client(
                timeout=timeout, follow_redirects=True, headers=headers, transport=transport, max_redirects=10
            ) as client,
            client.stream("GET", url) as response,
        ):
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > max_bytes:
                    raise FetchError(f"{url}: response is larger than {max_bytes // (1024 * 1024)} MB")
                chunks.append(chunk)
            body = b"".join(chunks)
            status = response.status_code
            final_url = str(response.url)
            content_type = response.headers.get("content-type", "")
            encoding = response.charset_encoding or "utf-8"
    except httpx.HTTPError as exc:
        raise FetchError(f"{url}: {exc.__class__.__name__}: {exc}") from exc
    if status >= 400:
        raise FetchError(f"{url}: HTTP {status}")
    kind = content_type.split(";")[0].strip().lower()
    if kind and not (
        kind in ("text/html", "application/xhtml+xml", "application/ld+json", "application/json")
        or kind.startswith("text/")
    ):
        raise FetchError(f"{url}: unsupported content type {kind}")
    try:
        text = body.decode(encoding, errors="replace")
    except LookupError:
        text = body.decode("utf-8", errors="replace")
    return Page(url=url, final_url=final_url, status=status, content_type=kind, text=text)
