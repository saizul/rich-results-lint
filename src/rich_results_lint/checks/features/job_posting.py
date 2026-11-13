"""JobPosting."""

from __future__ import annotations

import re

from ...model import Item
from ...values import as_datetime, is_iso_currency, parse_number
from ..base import Context
from .base import Feature

EMPLOYMENT_TYPES = {"FULL_TIME", "PART_TIME", "CONTRACTOR", "TEMPORARY", "INTERN", "VOLUNTEER", "PER_DIEM", "OTHER"}
SALARY_UNITS = {"HOUR", "DAY", "WEEK", "MONTH", "YEAR"}
_TITLE_NOISE = re.compile(
    r"[!*]|\$\s?\d|\b\d{4}-\d{2}-\d{2}\b|\b(?:urgent|hiring now|apply now)\b|#\d{3,}|\b[A-Z]{2,}-\d{2,}\b", re.I
)


class JobPosting(Feature):
    id = "job-posting"
    name = "Job posting"
    doc = "job-posting"
    types = ("JobPosting",)
    required = ("datePosted", "description", "hiringOrganization", "hiringOrganization.name", "title")
    recommended = ("baseSalary", "employmentType", "validThrough", "directApply", "identifier")

    def extra(self, ctx: Context, item: Item) -> None:
        remote = "TELECOMMUTE" in [t.strip().upper() for t in item.texts("jobLocationType")]
        for t in item.texts("jobLocationType"):
            if t.strip() != "TELECOMMUTE":
                self.report(
                    ctx,
                    "job/remote",
                    f'jobLocationType "{t}" is not supported; the only value is "TELECOMMUTE".',
                    item,
                    "jobLocationType",
                )
        if not item.has("jobLocation"):
            if not remote:
                self.report(ctx, "google/required", 'Missing required property "jobLocation" for Job posting.', item)
            elif not item.has("applicantLocationRequirements"):
                self.report(
                    ctx,
                    "job/remote",
                    "Remote jobs (TELECOMMUTE) need applicantLocationRequirements with at least one Country.",
                    item,
                )
        if remote and not item.has("applicantLocationRequirements") and item.has("jobLocation"):
            self.report(
                ctx,
                "job/remote",
                "Remote jobs need applicantLocationRequirements naming the countries applicants may live in.",
                item,
                "jobLocationType",
            )
        for place in ctx.items_of(item, "jobLocation"):
            addresses = ctx.items_of(place, "address")
            if not addresses:
                self.report(ctx, "job/location-country", "jobLocation has no PostalAddress.", place)
            for address in addresses:
                if not address.has("addressCountry"):
                    self.report(
                        ctx, "job/location-country", 'jobLocation.address needs addressCountry (e.g. "BD").', address
                    )
                self.check_paths(
                    ctx,
                    address,
                    ("addressLocality", "addressRegion", "postalCode", "streetAddress"),
                    "google/recommended",
                    "the job address",
                )
        for value in item.get("employmentType"):
            if isinstance(value, str) and value not in EMPLOYMENT_TYPES:
                hint = value.strip().upper().replace("-", "_").replace(" ", "_")
                extra = f' Use "{hint}".' if hint in EMPLOYMENT_TYPES else ""
                self.report(
                    ctx,
                    "job/employment-type",
                    f'employmentType "{value}" is not one of {", ".join(sorted(EMPLOYMENT_TYPES))} '
                    f"(case-sensitive).{extra}",
                    item,
                    "employmentType",
                )
        for salary in item.get("baseSalary"):
            self.check_salary(ctx, item, salary)
        self.check_text(ctx, item)
        self.check_dates(ctx, item)
        for org in ctx.items_of(item, "hiringOrganization"):
            self.check_paths(ctx, org, ("sameAs|url", "logo"), "google/recommended", "the hiring organization")

    def check_salary(self, ctx: Context, item: Item, salary: object) -> None:
        salary = ctx.resolve(salary)  # type: ignore[arg-type]
        if not isinstance(salary, Item):
            self.report(
                ctx, "job/salary", "baseSalary must be a MonetaryAmount, not a plain value.", item, "baseSalary"
            )
            return
        currency = salary.texts("currency")
        if not currency:
            self.report(ctx, "job/salary", 'baseSalary needs a currency (ISO 4217, e.g. "BDT").', salary)
        elif not is_iso_currency(currency[0]):
            self.report(
                ctx, "job/salary", f'baseSalary currency "{currency[0]}" is not an ISO 4217 code.', salary, "currency"
            )
        values = salary.get("value")
        if not values:
            self.report(
                ctx,
                "job/salary",
                "baseSalary needs a value (a QuantitativeValue with value or minValue/maxValue).",
                salary,
            )
        for v in values:
            v = ctx.resolve(v)
            if not isinstance(v, Item):
                if parse_number(v) is None:
                    self.report(ctx, "job/salary", f'baseSalary value "{v}" is not a number.', salary, "value")
                continue
            if not (v.has("value") or (v.has("minValue") and v.has("maxValue")) or v.has("minValue")):
                self.report(ctx, "job/salary", "The QuantitativeValue needs value, or minValue and maxValue.", v)
            lo, hi = parse_number(v.first("minValue")), parse_number(v.first("maxValue"))
            if lo is not None and hi is not None and lo > hi:
                self.report(ctx, "job/salary", "minValue is greater than maxValue.", v, "minValue")
            units = v.texts("unitText")
            if not units:
                self.report(ctx, "job/salary", "The salary needs unitText: HOUR, DAY, WEEK, MONTH or YEAR.", v)
            for unit in units:
                if unit not in SALARY_UNITS:
                    self.report(
                        ctx,
                        "job/salary",
                        f'unitText "{unit}" must be HOUR, DAY, WEEK, MONTH or YEAR (case-sensitive).',
                        v,
                        "unitText",
                    )

    def check_text(self, ctx: Context, item: Item) -> None:
        titles = item.texts("title")
        for title in titles:
            if _TITLE_NOISE.search(title):
                self.report(
                    ctx,
                    "job/title",
                    f'title "{title}" should be only the job title: no codes, salaries, dates, "!" or "*".',
                    item,
                    "title",
                )
        if not titles and item.has("name"):
            self.report(ctx, "job/title", 'Use "title" for the job title, not "name".', item, "name")
        for desc in item.texts("description"):
            plain = re.sub(r"<[^>]+>", " ", desc)
            plain = re.sub(r"\s+", " ", plain).strip()
            if titles and plain.lower() == titles[0].strip().lower():
                self.report(
                    ctx,
                    "job/description",
                    "description is the same as title; give the full job description.",
                    item,
                    "description",
                )
            elif len(plain) < 50:
                self.report(
                    ctx,
                    "job/description",
                    f"description is only {len(plain)} characters; give the full job description.",
                    item,
                    "description",
                )

    def check_dates(self, ctx: Context, item: Item) -> None:
        posted = next((as_datetime(s) for s in item.texts("datePosted") if as_datetime(s)), None)
        for raw in item.texts("validThrough"):
            through = as_datetime(raw)
            if through is None:
                continue
            if through < ctx.now:
                self.report(
                    ctx,
                    "job/expired",
                    f"validThrough {raw} is in the past; Google treats the job as expired.",
                    item,
                    "validThrough",
                )
            if posted and through < posted:
                self.report(ctx, "job/expired", "validThrough is before datePosted.", item, "validThrough")
        if posted and posted > ctx.now.replace(microsecond=0) and (posted - ctx.now).days > 1:
            self.report(ctx, "value/date", "datePosted is in the future.", item, "datePosted")


JOB_POSTING = JobPosting()
