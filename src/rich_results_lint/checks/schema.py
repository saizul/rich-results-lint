"""schema.org vocabulary, value format and @id graph checks. These run on every item, nested ones included."""

from __future__ import annotations

from ..model import Item, Severity, Syntax, Value
from ..values import (
    check_date_or_datetime,
    duration_error,
    has_time_without_timezone,
    is_iso_country,
    is_iso_currency,
    parse_number,
    url_problem,
)
from ..vocab import is_schema_iri, local_name
from .base import Context

#: Date-time properties where Google asks for a timezone.
TIMEZONE_PROPS = {"datePublished", "dateModified", "uploadDate", "startDate", "endDate", "expires", "previousStartDate"}
#: Properties Google reads as URLs even though their schema.org range is wider.
URL_PROPS = {"item", "image", "logo", "thumbnailUrl", "contentUrl", "embedUrl", "url", "sameAs", "menu", "hasMap"}
#: Numeric properties checked elsewhere with friendlier messages.
SKIP_NUMBER = {"price", "lowPrice", "highPrice", "ratingValue", "bestRating", "worstRating", "position"}
CURRENCY_PROPS = {"priceCurrency", "currency", "salaryCurrency"}
#: Superseded in schema.org but still the property Google documents.
GOOGLE_DOCUMENTED = {"menu"}
_NUMERIC = {"Number", "Integer", "Float"}
_TRUE_FALSE = {
    "true",
    "false",
    "https://schema.org/true",
    "https://schema.org/false",
    "http://schema.org/true",
    "http://schema.org/false",
}


def check_items(ctx: Context, items: list[Item]) -> None:
    seen: dict[str, Item] = {}
    for top in items:
        for item, _path in top.walk():
            _check_types(ctx, item, nested=item is not top)
            _check_properties(ctx, item)
            if item.id and not item.is_reference:
                prev = seen.get(item.id)
                if prev is not None and prev.types and item.types and set(prev.types) != set(item.types):
                    ctx.report(
                        "graph/duplicate-id",
                        f'@id "{item.id}" is defined as {prev.label()} (line {prev.line}) and as {item.label()}.',
                        item=item,
                    )
                seen.setdefault(item.id, item)
    for top in items:
        for item, _path in top.walk():
            if item.is_reference and item.id not in ctx.ids:
                ctx.report(
                    "graph/unresolved-id",
                    f'@id "{item.id}" is referenced but no node with that @id is defined on the page. Google does not '
                    "fetch other pages to resolve it.",
                    item=item,
                )


def _check_types(ctx: Context, item: Item, nested: bool) -> None:
    if item.is_reference:
        return
    if not item.types:
        if item.properties and (item.syntax is Syntax.JSON_LD or not nested):
            ctx.report(
                "schema/missing-type",
                "This object has no @type." if nested else "This item has no type, so no rich result can use it.",
                item=item,
                severity=None if nested else Severity.WARNING,
            )
        return
    for raw, name in zip(item.raw_types, item.types, strict=False):
        if raw.startswith(("http://", "https://")) and not is_schema_iri(raw):
            ctx.report("schema/external-type", f'Type "{raw}" is not from schema.org and is not checked.', item=item)
            continue
        if ":" in name or "/" in name:
            ctx.report("schema/external-type", f'Type "{raw}" is not from schema.org and is not checked.', item=item)
            continue
        if not ctx.vocab.is_type(name):
            hint = ctx.vocab.suggest_type(name)
            ctx.report(
                "schema/unknown-type",
                f'"{name}" is not a schema.org type.' + (f' Did you mean "{hint}"?' if hint else ""),
                item=item,
            )


def _check_properties(ctx: Context, item: Item) -> None:
    known_types = [t for t in item.types if ctx.vocab.is_type(t)]
    for name, values in item.properties.items():
        if ":" in name or "/" in name or name.endswith(("-input", "-output")):
            continue  # another vocabulary, or a Schema.org Action input/output annotation
        if not ctx.vocab.is_property(name):
            hint = ctx.vocab.suggest_property(name, known_types)
            ctx.report(
                "schema/unknown-property",
                f'"{name}" is not a schema.org property.' + (f' Did you mean "{hint}"?' if hint else ""),
                item=item,
                prop=name,
            )
            continue
        replacement = ctx.vocab.superseded_by(name)
        if replacement and name not in GOOGLE_DOCUMENTED:
            ctx.report(
                "schema/superseded-property",
                f'"{name}" is superseded by "{replacement}" in schema.org.',
                item=item,
                prop=name,
            )
        elif known_types and len(known_types) == len(item.types) and not ctx.vocab.expects(known_types, name):
            ctx.report(
                "schema/unexpected-property",
                f'"{name}" is not defined for {item.label()} in schema.org.',
                item=item,
                prop=name,
            )
        for value in values:
            if not isinstance(value, Item):
                _check_value(ctx, item, name, value)


def _check_value(ctx: Context, item: Item, prop: str, value: Value) -> None:
    if value is None:
        ctx.report("value/empty", f'"{prop}" is null.', item=item, prop=prop)
        return
    ranges = set(ctx.vocab.ranges(prop))
    text = value if isinstance(value, str) else None
    if text is not None and not text.strip():
        ctx.report("value/empty", f'"{prop}" is empty.', item=item, prop=prop)
        return
    textual = "Text" in ranges

    if text is not None and ranges & {"Date", "DateTime"} and not textual:
        problem = check_date_or_datetime(text, allow_date="Date" in ranges or "DateTime" in ranges)
        if problem:
            ctx.report("value/date", f"{prop}: {problem}", item=item, prop=prop)
        elif prop in TIMEZONE_PROPS and has_time_without_timezone(text):
            ctx.report(
                "value/timezone",
                f'{prop} "{text}" has no timezone offset; Google then assumes its own timezone. Add one, '
                'for example "+06:00".',
                item=item,
                prop=prop,
            )
        return

    if text is not None and "Duration" in ranges and not textual:
        problem = duration_error(text)
        if problem:
            ctx.report("value/duration", f"{prop}: {problem}", item=item, prop=prop)
        return

    if text is not None and (("URL" in ranges and not textual) or prop in URL_PROPS):
        problem = url_problem(text)
        if problem:
            rule, message = problem
            if rule == "value/url-relative" and item.syntax is not Syntax.JSON_LD:
                return  # Microdata and RDFa links are resolved against the page URL like any link.
            if rule == "value/url-relative" and ctx.doc.url:
                message += f" (it resolves against {ctx.doc.url})"
            ctx.report(rule, f"{prop}: {message}", item=item, prop=prop)
        return

    if prop in CURRENCY_PROPS and text is not None:
        if not is_iso_currency(text):
            hint = f' Did you mean "{text.strip().upper()}"?' if is_iso_currency(text.strip().upper()) else ""
            ctx.report(
                "value/currency",
                f'{prop} "{text}" is not a three-letter ISO 4217 currency code (BDT, USD, EUR).{hint}',
                item=item,
                prop=prop,
            )
        return

    if prop == "addressCountry" and text is not None:
        if not is_iso_country(text):
            hint = f' Did you mean "{text.strip().upper()}"?' if is_iso_country(text.strip().upper()) else ""
            ctx.report(
                "value/country",
                f'addressCountry "{text}" is not a two-letter ISO 3166-1 code (BD, US, GB).{hint}',
                item=item,
                prop=prop,
            )
        return

    if ranges == {"Boolean"}:
        if not isinstance(value, bool) and str(value).strip().lower() not in _TRUE_FALSE:
            ctx.report("value/boolean", f'{prop} should be true or false, not "{value}".', item=item, prop=prop)
        return

    if ranges and ranges <= _NUMERIC and prop not in SKIP_NUMBER:
        if parse_number(value) is None:
            ctx.report("value/number", f'{prop} should be a number, not "{value}".', item=item, prop=prop)
        return

    enums = [r for r in ranges if ctx.vocab.is_subtype(r, "Enumeration")]
    if text is not None and enums and (not ranges & {"Text", "URL"} or is_schema_iri(text)):
        member = local_name(text)
        if not any(ctx.vocab.is_subtype(e, *enums) for e in ctx.vocab.enum_of(member)):
            hint = None
            for e in enums:
                hint = hint or ctx.vocab.suggest_member(member, e)
            ctx.report(
                "schema/invalid-enum",
                f'{prop} "{text}" is not an allowed {"/".join(sorted(enums))} value.'
                + (f' Use "https://schema.org/{hint}".' if hint else ""),
                item=item,
                prop=prop,
            )
