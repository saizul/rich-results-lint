from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest

from rich_results_lint.values import (
    as_datetime,
    check_date_or_datetime,
    decimals,
    duration_error,
    has_time_without_timezone,
    is_iso_country,
    is_iso_currency,
    parse_date,
    parse_datetime,
    parse_duration,
    parse_price,
    parse_rating,
    url_problem,
)


@pytest.mark.parametrize(
    "value",
    [
        "2026-11-13",
        "2026-02-28",
        "2024-02-29",
        "2026-11-13T10:00",
        "2026-11-13T10:00:00",
        "2026-11-13T10:00:00Z",
        "2026-11-13T10:00:00+06:00",
        "2026-11-13T10:00:00.123-05:30",
        "2026-11-13T10:00:00+0600",
        "2026-11-13T24:00:00",
        "2026",
        "2026-11",
    ],
)
def test_valid_dates(value: str) -> None:
    assert check_date_or_datetime(value) is None


@pytest.mark.parametrize(
    ("value", "hint"),
    [
        ("13/11/2026", "YYYY-MM-DD"),
        ("2026-13-01", "Check"),
        ("2025-02-29", "Check"),
        ("2026-11-13 10:00:00", '"T"'),
        ("2026-11-13T25:00", "Check"),
        ("November 13, 2026", ""),
        ("2026-11-13T10:00:00+15:00", "Check"),
        ("", ""),
    ],
)
def test_invalid_dates(value: str, hint: str) -> None:
    message = check_date_or_datetime(value)
    assert message is not None
    assert hint in message


def test_parse_date_and_datetime() -> None:
    assert parse_date("2026-11-13").day == 13
    assert parse_date("2026-11-13T00:00") is None
    dt, tz = parse_datetime("2026-11-13T10:00:00+06:00")
    assert tz and dt is not None and dt.utcoffset() == timedelta(hours=6)
    dt, tz = parse_datetime("2026-11-13T10:00")
    assert not tz and dt is not None
    assert parse_datetime("nope") == (None, False)
    assert has_time_without_timezone("2026-11-13T10:00")
    assert not has_time_without_timezone("2026-11-13T10:00Z")
    assert not has_time_without_timezone("2026-11-13")


def test_as_datetime_compares_dates_and_times() -> None:
    assert as_datetime("2026-01-01") < as_datetime("2026-01-01T10:00:00Z")
    assert as_datetime("garbage") is None


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("PT1H30M", timedelta(hours=1, minutes=30)),
        ("PT45S", timedelta(seconds=45)),
        ("PT1M54S", timedelta(minutes=1, seconds=54)),
        ("P1D", timedelta(days=1)),
        ("P1W", timedelta(days=7)),
        ("PT0.5S", timedelta(seconds=0.5)),
        ("P1DT2H", timedelta(days=1, hours=2)),
        ("PT00H30M5S", timedelta(minutes=30, seconds=5)),
    ],
)
def test_valid_durations(value: str, expected: timedelta) -> None:
    assert parse_duration(value) == expected
    assert duration_error(value) is None


@pytest.mark.parametrize(
    ("value", "hint"),
    [
        ("P", ""),
        ("PT", ""),
        ("1H30M", ""),
        ("P1H", "after"),
        ("30 minutes", "PT30M"),
        ("PT10M-PT20M", "Ranges"),
        ("PT10-20M", "Ranges"),
        ("10 to 20 minutes", "Ranges"),
        ("pt1h", ""),
    ],
)
def test_invalid_durations(value: str, hint: str) -> None:
    message = duration_error(value)
    assert message is not None and hint in message


@pytest.mark.parametrize(
    ("value", "rule"),
    [
        ("https://example.com/a", None),
        ("http://example.com", None),
        ("mailto:a@example.com", None),
        ("tel:+8801700000000", None),
        ("/products/1", "value/url-relative"),
        ("products/1", "value/url-relative"),
        ("//cdn.example.com/x.jpg", "value/url-relative"),
        ("https://example.com/a b.jpg", "value/url-invalid"),
        ("https://", "value/url-invalid"),
        ("javascript:void(0)", "value/url-invalid"),
    ],
)
def test_url_problem(value: str, rule: str | None) -> None:
    result = url_problem(value)
    assert (result[0] if result else None) == rule


@pytest.mark.parametrize(
    ("value", "amount"),
    [
        (39.99, Decimal("39.99")),
        ("39.99", Decimal("39.99")),
        (1200, Decimal("1200")),
        ("0", Decimal("0")),
        ("1500.5", Decimal("1500.5")),
    ],
)
def test_valid_prices(value: object, amount: Decimal) -> None:
    assert parse_price(value) == (amount, None)


@pytest.mark.parametrize(
    ("value", "fragment"),
    [
        ("$39.99", "currency"),
        ("৳1200", "currency"),
        ("1200 BDT", "currency"),
        ("Tk. 500", "currency"),
        ("1,299.00", "thousands"),
        ("10,50", "decimal"),
        ("100-200", "range"),
        ("", "empty"),
        ("free", "plain number"),
        (True, "boolean"),
        (None, "not a number"),
    ],
)
def test_invalid_prices(value: object, fragment: str) -> None:
    amount, problem = parse_price(value)
    assert amount is None and problem is not None and fragment in problem


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (4, (4.0, None)),
        ("4.5", (4.5, None)),
        ("60%", (60.0, 100.0)),
        ("6 / 10", (6.0, 10.0)),
        ("4,4", (4.4, None)),
        ("good", (None, None)),
    ],
)
def test_parse_rating(value: object, expected: tuple) -> None:
    assert parse_rating(value) == expected


def test_currency_and_country_codes() -> None:
    assert is_iso_currency("BDT") and is_iso_currency("USD") and is_iso_currency("EUR")
    assert not is_iso_currency("Tk") and not is_iso_currency("bdt") and not is_iso_currency("BTC")
    assert is_iso_country("BD") and is_iso_country("GB")
    assert (
        not is_iso_country("bd")
        and not is_iso_country("BGD")
        and not is_iso_country("Bangladesh")
        and not is_iso_country("XX")
    )


def test_decimals() -> None:
    assert decimals(23.746466) == 6
    assert decimals("90.4") == 1
    assert decimals(90) == 0
    assert decimals("north") is None
