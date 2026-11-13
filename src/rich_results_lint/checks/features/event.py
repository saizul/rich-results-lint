"""Event and its subtypes."""

from __future__ import annotations

from ...model import Item, Severity
from ...values import as_datetime
from ...vocab import local_name
from ..base import Context
from .base import Feature
from .review import REVIEW_SNIPPET

STATUSES = {"EventScheduled", "EventCancelled", "EventPostponed", "EventRescheduled"}


class Event(Feature):
    id = "event"
    name = "Event"
    doc = "event"
    types = ("Event",)
    required = ("name", "startDate", "location", "location.address")
    recommended = (
        "description",
        "endDate",
        "eventStatus",
        "image",
        "location.name",
        "offers",
        "organizer",
        "performer",
    )

    def extra(self, ctx: Context, item: Item) -> None:
        locations = [ctx.resolve(v) for v in item.get("location")]
        physical = [loc for loc in locations if isinstance(loc, Item) and not ctx.is_a(loc, "VirtualLocation")]
        for loc in locations:
            if isinstance(loc, str):
                self.report(
                    ctx,
                    "google/required",
                    "location is text; use a Place with a name and a PostalAddress.",
                    item,
                    "location",
                )
        mode = [local_name(m) for m in item.texts("eventAttendanceMode")]
        if (
            locations and not physical and any(isinstance(loc, Item) for loc in locations)
        ) or "OnlineEventAttendanceMode" in mode:
            self.report(
                ctx,
                "event/online-only",
                "This is an online-only event. Google removed online event support on 2025-06-05: events must take "
                "place at a physical location.",
                item,
            )
        for status in item.texts("eventStatus"):
            name = local_name(status)
            if name not in STATUSES:
                self.report(
                    ctx,
                    "event/status",
                    f'eventStatus "{status}" is not one of EventScheduled, EventCancelled, EventPostponed or '
                    "EventRescheduled.",
                    item,
                    "eventStatus",
                )
        statuses = {local_name(s) for s in item.texts("eventStatus")}
        if item.has("previousStartDate") and "EventRescheduled" not in statuses:
            self.report(
                ctx,
                "event/dates",
                "previousStartDate is only used with eventStatus EventRescheduled.",
                item,
                "previousStartDate",
                severity=Severity.WARNING,
            )
        start = next((as_datetime(s) for s in item.texts("startDate") if as_datetime(s)), None)
        end = next((as_datetime(s) for s in item.texts("endDate") if as_datetime(s)), None)
        if start and end and end < start:
            self.report(ctx, "event/dates", "endDate is before startDate.", item, "endDate")
        for offer in ctx.items_of(item, "offers"):
            self.check_paths(
                ctx,
                offer,
                ("price", "priceCurrency", "availability", "url", "validFrom"),
                "google/recommended",
                "event offers",
            )
        for organizer in ctx.items_of(item, "organizer"):
            self.check_paths(ctx, organizer, ("name", "url"), "google/recommended", "the organizer")
        for performer in ctx.items_of(item, "performer"):
            self.check_paths(ctx, performer, ("name",), "google/recommended", "the performer")
        REVIEW_SNIPPET.check_nested(ctx, item)


EVENT = Event()
