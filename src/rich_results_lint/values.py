"""Value parsers and validators: ISO 8601 dates and durations, URLs, prices, currencies, countries."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit

_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DATE_PARTIAL = re.compile(r"^(\d{4})(?:-(\d{2}))?$")
_DATETIME = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,9}))?)?"
    r"(?P<tz>[Zz]|[+-]\d{2}(?::?\d{2})?)?$"
)
_DURATION = re.compile(
    r"^P(?!$)(?:(?P<y>\d+(?:[.,]\d+)?)Y)?(?:(?P<mo>\d+(?:[.,]\d+)?)M)?(?:(?P<w>\d+(?:[.,]\d+)?)W)?"
    r"(?:(?P<d>\d+(?:[.,]\d+)?)D)?(?:T(?=\d)(?:(?P<h>\d+(?:[.,]\d+)?)H)?(?:(?P<mi>\d+(?:[.,]\d+)?)M)?"
    r"(?:(?P<s>\d+(?:[.,]\d+)?)S)?)?$"
)

ISO_4217 = frozenset(
    [
        "AED",
        "AFN",
        "ALL",
        "AMD",
        "ANG",
        "AOA",
        "ARS",
        "AUD",
        "AWG",
        "AZN",
        "BAM",
        "BBD",
        "BDT",
        "BGN",
        "BHD",
        "BIF",
        "BMD",
        "BND",
        "BOB",
        "BOV",
        "BRL",
        "BSD",
        "BTN",
        "BWP",
        "BYN",
        "BZD",
        "CAD",
        "CDF",
        "CHE",
        "CHF",
        "CHW",
        "CLF",
        "CLP",
        "CNY",
        "COP",
        "COU",
        "CRC",
        "CUP",
        "CVE",
        "CZK",
        "DJF",
        "DKK",
        "DOP",
        "DZD",
        "EGP",
        "ERN",
        "ETB",
        "EUR",
        "FJD",
        "FKP",
        "GBP",
        "GEL",
        "GHS",
        "GIP",
        "GMD",
        "GNF",
        "GTQ",
        "GYD",
        "HKD",
        "HNL",
        "HTG",
        "HUF",
        "IDR",
        "ILS",
        "INR",
        "IQD",
        "IRR",
        "ISK",
        "JMD",
        "JOD",
        "JPY",
        "KES",
        "KGS",
        "KHR",
        "KMF",
        "KPW",
        "KRW",
        "KWD",
        "KYD",
        "KZT",
        "LAK",
        "LBP",
        "LKR",
        "LRD",
        "LSL",
        "LYD",
        "MAD",
        "MDL",
        "MGA",
        "MKD",
        "MMK",
        "MNT",
        "MOP",
        "MRU",
        "MUR",
        "MVR",
        "MWK",
        "MXN",
        "MXV",
        "MYR",
        "MZN",
        "NAD",
        "NGN",
        "NIO",
        "NOK",
        "NPR",
        "NZD",
        "OMR",
        "PAB",
        "PEN",
        "PGK",
        "PHP",
        "PKR",
        "PLN",
        "PYG",
        "QAR",
        "RON",
        "RSD",
        "RUB",
        "RWF",
        "SAR",
        "SBD",
        "SCR",
        "SDG",
        "SEK",
        "SGD",
        "SHP",
        "SLE",
        "SLL",
        "SOS",
        "SRD",
        "SSP",
        "STN",
        "SVC",
        "SYP",
        "SZL",
        "THB",
        "TJS",
        "TMT",
        "TND",
        "TOP",
        "TRY",
        "TTD",
        "TWD",
        "TZS",
        "UAH",
        "UGX",
        "USD",
        "USN",
        "UYI",
        "UYU",
        "UYW",
        "UZS",
        "VED",
        "VES",
        "VND",
        "VUV",
        "WST",
        "XAF",
        "XCD",
        "XCG",
        "XOF",
        "XPF",
        "YER",
        "ZAR",
        "ZMW",
        "ZWG",
        "ZWL",
    ]
)

ISO_3166_ALPHA2 = frozenset(
    [
        "AD",
        "AE",
        "AF",
        "AG",
        "AI",
        "AL",
        "AM",
        "AO",
        "AQ",
        "AR",
        "AS",
        "AT",
        "AU",
        "AW",
        "AX",
        "AZ",
        "BA",
        "BB",
        "BD",
        "BE",
        "BF",
        "BG",
        "BH",
        "BI",
        "BJ",
        "BL",
        "BM",
        "BN",
        "BO",
        "BQ",
        "BR",
        "BS",
        "BT",
        "BV",
        "BW",
        "BY",
        "BZ",
        "CA",
        "CC",
        "CD",
        "CF",
        "CG",
        "CH",
        "CI",
        "CK",
        "CL",
        "CM",
        "CN",
        "CO",
        "CR",
        "CU",
        "CV",
        "CW",
        "CX",
        "CY",
        "CZ",
        "DE",
        "DJ",
        "DK",
        "DM",
        "DO",
        "DZ",
        "EC",
        "EE",
        "EG",
        "EH",
        "ER",
        "ES",
        "ET",
        "FI",
        "FJ",
        "FK",
        "FM",
        "FO",
        "FR",
        "GA",
        "GB",
        "GD",
        "GE",
        "GF",
        "GG",
        "GH",
        "GI",
        "GL",
        "GM",
        "GN",
        "GP",
        "GQ",
        "GR",
        "GS",
        "GT",
        "GU",
        "GW",
        "GY",
        "HK",
        "HM",
        "HN",
        "HR",
        "HT",
        "HU",
        "ID",
        "IE",
        "IL",
        "IM",
        "IN",
        "IO",
        "IQ",
        "IR",
        "IS",
        "IT",
        "JE",
        "JM",
        "JO",
        "JP",
        "KE",
        "KG",
        "KH",
        "KI",
        "KM",
        "KN",
        "KP",
        "KR",
        "KW",
        "KY",
        "KZ",
        "LA",
        "LB",
        "LC",
        "LI",
        "LK",
        "LR",
        "LS",
        "LT",
        "LU",
        "LV",
        "LY",
        "MA",
        "MC",
        "MD",
        "ME",
        "MF",
        "MG",
        "MH",
        "MK",
        "ML",
        "MM",
        "MN",
        "MO",
        "MP",
        "MQ",
        "MR",
        "MS",
        "MT",
        "MU",
        "MV",
        "MW",
        "MX",
        "MY",
        "MZ",
        "NA",
        "NC",
        "NE",
        "NF",
        "NG",
        "NI",
        "NL",
        "NO",
        "NP",
        "NR",
        "NU",
        "NZ",
        "OM",
        "PA",
        "PE",
        "PF",
        "PG",
        "PH",
        "PK",
        "PL",
        "PM",
        "PN",
        "PR",
        "PS",
        "PT",
        "PW",
        "PY",
        "QA",
        "RE",
        "RO",
        "RS",
        "RU",
        "RW",
        "SA",
        "SB",
        "SC",
        "SD",
        "SE",
        "SG",
        "SH",
        "SI",
        "SJ",
        "SK",
        "SL",
        "SM",
        "SN",
        "SO",
        "SR",
        "SS",
        "ST",
        "SV",
        "SX",
        "SY",
        "SZ",
        "TC",
        "TD",
        "TF",
        "TG",
        "TH",
        "TJ",
        "TK",
        "TL",
        "TM",
        "TN",
        "TO",
        "TR",
        "TT",
        "TV",
        "TW",
        "TZ",
        "UA",
        "UG",
        "UM",
        "US",
        "UY",
        "UZ",
        "VA",
        "VC",
        "VE",
        "VG",
        "VI",
        "VN",
        "VU",
        "WF",
        "WS",
        "YE",
        "YT",
        "ZA",
        "ZM",
        "ZW",
    ]
)

_CURRENCY_SIGNS = re.compile(r"[$€£¥₹৳₽₩₺₦₱₴₫₪฿]|\b(?:tk|taka|usd|eur|bdt|rs|inr|gbp)\b", re.IGNORECASE)


def parse_date(value: str) -> date | None:
    """A complete calendar date ``YYYY-MM-DD``."""
    m = _DATE.match(value.strip())
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def parse_datetime(value: str) -> tuple[datetime | None, bool]:
    """An ISO 8601 date-time. Returns (value, has_timezone). Naive values are returned as UTC for comparisons."""
    m = _DATETIME.match(value.strip())
    if not m:
        return None, False
    y, mo, d, h, mi = (int(m.group(i)) for i in range(1, 6))
    s = int(m.group(6) or 0)
    tz_text = m.group("tz")
    try:
        if h == 24 and mi == 0 and s == 0:
            base = datetime(y, mo, d) + timedelta(days=1)
        else:
            base = datetime(y, mo, d, h, mi, s)
    except ValueError:
        return None, False
    if not tz_text:
        return base.replace(tzinfo=timezone.utc), False
    if tz_text in ("Z", "z"):
        return base.replace(tzinfo=timezone.utc), True
    sign = 1 if tz_text[0] == "+" else -1
    digits = tz_text[1:].replace(":", "")
    hours, minutes = int(digits[:2]), int(digits[2:4] or 0)
    if hours > 14 or minutes > 59:
        return None, False
    return base.replace(tzinfo=timezone(sign * timedelta(hours=hours, minutes=minutes))), True


def check_date_or_datetime(value: str, allow_date: bool = True, allow_datetime: bool = True) -> str | None:
    """Return an error message, or None when the value is valid."""
    v = value.strip()
    if allow_date and parse_date(v):
        return None
    if allow_datetime and parse_datetime(v)[0] is not None:
        return None
    if allow_date and _DATE_PARTIAL.match(v):
        return None  # A year or year-month is valid ISO 8601, if not very useful.
    hint = ""
    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}", v):
        hint = ' Use "T" between date and time.'
    elif re.match(r"^\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}$", v):
        hint = " Use YYYY-MM-DD."
    elif re.match(r"^\d{4}-\d{2}-\d{2}", v):
        hint = " Check the month, day and time values."
    return f'"{value}" is not a valid ISO 8601 date or date-time.{hint}'


def as_datetime(value: str) -> datetime | None:
    """Date or date-time as an aware datetime (dates at 00:00 UTC), for comparisons."""
    d = parse_date(value)
    if d:
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    return parse_datetime(value)[0]


def has_time_without_timezone(value: str) -> bool:
    dt, has_tz = parse_datetime(value)
    return dt is not None and not has_tz


def parse_duration(value: str) -> timedelta | None:
    """An ISO 8601 duration. Years and months are counted as 365 and 30 days."""
    m = _DURATION.match(value.strip())
    if not m or value.strip().endswith("T"):
        return None

    def num(name: str) -> float:
        g = m.group(name)
        return float(g.replace(",", ".")) if g else 0.0

    days = num("y") * 365 + num("mo") * 30 + num("w") * 7 + num("d")
    return timedelta(days=days, hours=num("h"), minutes=num("mi"), seconds=num("s"))


def duration_error(value: str) -> str | None:
    if parse_duration(value) is not None:
        return None
    v = value.strip()
    hint = ""
    if re.search(r"\d+\s*-\s*\d+|PT\d+M?-", v) or " to " in v:
        hint = " Ranges are not supported; give one exact time."
    elif re.match(r"^\d+\s*(min|mins|minutes|m|h|hours?)$", v, re.IGNORECASE):
        hint = ' Write it as "PT30M" or "PT1H".'
    elif v.startswith("P") and "T" not in v and re.search(r"\d+[HS]", v):
        hint = ' Hours, minutes and seconds go after "T": "PT1H30M".'
    return f'"{value}" is not a valid ISO 8601 duration.{hint}'


def url_problem(value: str) -> tuple[str, str] | None:
    """Return (rule, message) for a bad URL, or None."""
    v = value.strip()
    if not v:
        return None
    if re.search(r"\s", v):
        return "value/url-invalid", f'"{value}" contains spaces; encode them as %20.'
    parts = urlsplit(v)
    if parts.scheme:
        if parts.scheme.lower() in ("http", "https"):
            if not parts.netloc:
                return "value/url-invalid", f'"{value}" has no host name.'
            return None
        if parts.scheme.lower() in ("mailto", "tel", "data"):
            return None
        if parts.scheme.lower() == "javascript":
            return "value/url-invalid", f'"{value}" is a javascript: link, not a URL.'
        return None
    if v.startswith("//"):
        return "value/url-relative", f'"{value}" is protocol-relative; add https:.'
    return "value/url-relative", f'"{value}" is a relative URL; use an absolute URL.'


def parse_price(value: object) -> tuple[Decimal | None, str | None]:
    """Parse a price. Returns (amount, problem). A problem is set for values Google does not accept."""
    if isinstance(value, bool):
        return None, "is a boolean, not a number"
    if isinstance(value, (int, float)):
        return Decimal(str(value)), None
    if not isinstance(value, str):
        return None, "is not a number"
    v = value.strip()
    if not v:
        return None, "is empty"
    if _CURRENCY_SIGNS.search(v):
        return None, "contains a currency symbol or code; put the currency in priceCurrency"
    if re.search(r"\d\s*[-–]\s*\d", v):
        return None, "is a range; use AggregateOffer with lowPrice and highPrice"
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", v):
        return None, 'uses "," as a thousands separator; write the number without separators'
    if re.fullmatch(r"\d+,\d{1,2}", v):
        return None, 'uses "," as the decimal separator; use "."'
    if re.fullmatch(r"\d+(?:\.\d+)?", v):
        try:
            return Decimal(v), None
        except InvalidOperation:  # pragma: no cover - regex guarantees a number
            return None, "is not a number"
    return None, "is not a plain number"


def parse_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and re.fullmatch(r"\s*-?\d+(?:\.\d+)?\s*", value):
        return float(value)
    return None


def parse_rating(value: object) -> tuple[float | None, float | None]:
    """A rating value: number, percentage (``60%``) or fraction (``6/10``).

    Returns (value, implied_best): implied_best is set for percentages (100) and fractions (the denominator).
    """
    n = parse_number(value)
    if n is not None:
        return n, None
    if isinstance(value, str):
        v = value.strip()
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*%", v)
        if m:
            return float(m.group(1)), 100.0
        m = re.fullmatch(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", v)
        if m:
            return float(m.group(1)), float(m.group(2))
        m = re.fullmatch(r"(\d+),(\d+)", v)
        if m:
            return float(f"{m.group(1)}.{m.group(2)}"), None
    return None, None


def is_iso_currency(value: str) -> bool:
    return value.strip() in ISO_4217


def is_iso_country(value: str) -> bool:
    return value.strip().upper() in ISO_3166_ALPHA2 and value.strip().isupper()


def decimals(value: object) -> int | None:
    """Number of decimal places in a coordinate."""
    text = repr(value) if isinstance(value, float) else str(value).strip()
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", text):
        return None
    return len(text.split(".")[1]) if "." in text else 0
