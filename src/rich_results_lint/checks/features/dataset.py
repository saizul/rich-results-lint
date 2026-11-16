"""Dataset, with DataDownload distributions and DataCatalog membership."""

from __future__ import annotations

import re

from ...model import Item
from ...values import check_date_or_datetime
from ..base import Context
from .base import Feature, info

DESCRIPTION_MIN = 50
DESCRIPTION_MAX = 5000
#: ISO 8601 interval with open ends (``..``), as Google documents for temporalCoverage.
_INTERVAL = re.compile(r"^(?P<start>[^/]+)/(?P<end>[^/]+)$")


class Dataset(Feature):
    id = "dataset"
    name = "Dataset"
    doc = "dataset"
    types = ("Dataset",)
    required = ("description", "name")
    recommended = (
        "creator",
        "creator.name",
        "distribution",
        "keywords",
        "license",
        "url",
        "temporalCoverage|spatialCoverage",
    )

    def extra(self, ctx: Context, item: Item) -> None:
        for text in item.texts("description"):
            n = len(text.strip())
            if n < DESCRIPTION_MIN or n > DESCRIPTION_MAX:
                self.report(
                    ctx,
                    "dataset/description",
                    f"description has {n} characters; Google needs {DESCRIPTION_MIN} to {DESCRIPTION_MAX}.",
                    item,
                    "description",
                )
        names = {t.strip().casefold() for t in item.texts("name")}
        if names and any(t.strip().casefold() in names for t in item.texts("description")):
            self.report(ctx, "dataset/description", "description repeats the name.", item, "description")
        for creator in item.get("creator"):
            if isinstance(ctx.resolve(creator), str):
                info(
                    ctx,
                    self,
                    "dataset/creator",
                    f'creator "{creator}" is text; use a Person or Organization with a name.',
                    item,
                    "creator",
                )
        for creator in ctx.items_of(item, "creator"):
            if creator.types and not ctx.is_a(creator, "Person", "Organization"):
                self.report(
                    ctx, "dataset/creator", f"creator is a {creator.label()}; use Person or Organization.", creator
                )
        for value in item.get("distribution"):
            dist = ctx.resolve(value)
            if not isinstance(dist, Item):
                self.report(
                    ctx,
                    "dataset/distribution",
                    "distribution is text; use a DataDownload with contentUrl and encodingFormat.",
                    item,
                    "distribution",
                )
                continue
            if dist.types and not ctx.is_a(dist, "DataDownload"):
                self.report(
                    ctx,
                    "dataset/distribution",
                    f"distribution is a {dist.label()}; use DataDownload.",
                    dist,
                )
            if not dist.has("contentUrl"):
                self.report(ctx, "dataset/distribution", 'The DataDownload needs "contentUrl".', dist)
            self.check_paths(ctx, dist, ("encodingFormat",), "google/recommended", "a DataDownload")
        for value in item.get("includedInDataCatalog"):
            catalog = ctx.resolve(value)
            if isinstance(catalog, Item) and not catalog.has("name"):
                self.report(ctx, "google/recommended", 'The DataCatalog needs "name".', catalog)
        for raw in item.texts("temporalCoverage"):
            problem = temporal_problem(raw)
            if problem:
                self.report(
                    ctx, "dataset/temporal-coverage", f'temporalCoverage "{raw}" {problem}.', item, "temporalCoverage"
                )
        not_free = item.first("isAccessibleForFree") in (False, "false", "False")
        if item.has("isAccessibleForFree") and not_free and not item.has("license"):
            info(
                ctx,
                self,
                "dataset/license",
                "The dataset is not free to access; say how it can be used with license.",
                item,
                "isAccessibleForFree",
            )


def temporal_problem(value: str) -> str | None:
    """Why a temporalCoverage value is not an ISO 8601 date, date-time or interval, or None when it is fine."""
    text = value.strip()
    if not text:
        return "is empty"
    m = _INTERVAL.match(text)
    if m is None:
        if check_date_or_datetime(text) is None:
            return None
        return "is not an ISO 8601 date or interval (2008, 2008-01/2008-12, 2010/..)"
    start, end = m.group("start"), m.group("end")
    if start == ".." and end == "..":
        return "has two open ends"
    for part in (start, end):
        if part == ".." or check_date_or_datetime(part) is None:
            continue
        return f'has "{part}", which is not an ISO 8601 date'
    if start != ".." and end != ".." and len(start) == len(end) and end < start:
        return "ends before it starts"
    return None


DATASET = Dataset()
