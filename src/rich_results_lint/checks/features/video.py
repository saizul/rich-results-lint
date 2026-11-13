"""VideoObject, with Clip, SeekToAction and BroadcastEvent."""

from __future__ import annotations

from ...model import Item
from ...values import as_datetime, parse_number
from ..base import Context
from .base import Feature


class Video(Feature):
    id = "video"
    name = "Video"
    doc = "video"
    types = ("VideoObject",)
    required = ("name", "thumbnailUrl", "uploadDate")
    recommended = ("contentUrl|embedUrl", "description", "duration")

    def extra(self, ctx: Context, item: Item) -> None:
        if item.has("regionsAllowed") and item.has("ineligibleRegion"):
            self.report(
                ctx,
                "video/regions",
                "Use either regionsAllowed or ineligibleRegion, not both.",
                item,
                "ineligibleRegion",
            )
        for raw in item.texts("expires"):
            when = as_datetime(raw)
            if when is not None and when < ctx.now:
                self.report(
                    ctx, "video/expired", f"expires {raw} is in the past; the video will not be shown.", item, "expires"
                )
        page = ctx.doc.url
        for url in item.texts("contentUrl"):
            if page and url.rstrip("/") == page.rstrip("/"):
                self.report(
                    ctx,
                    "video/clips",
                    "contentUrl is the page URL; it must point to the video file.",
                    item,
                    "contentUrl",
                )
        clips = [c for c in ctx.items_of(item, "hasPart") if ctx.is_a(c, "Clip")]
        offsets: dict[float, Item] = {}
        for clip in clips:
            for prop in ("name", "startOffset", "url"):
                if not clip.has(prop):
                    self.report(ctx, "video/clips", f'The Clip needs "{prop}".', clip)
            start = parse_number(clip.first("startOffset")) if clip.has("startOffset") else None
            end = parse_number(clip.first("endOffset")) if clip.has("endOffset") else None
            if start is not None:
                if start in offsets:
                    self.report(ctx, "video/clips", f"Two clips start at {start:g} seconds.", clip, "startOffset")
                offsets[start] = clip
                if end is not None and end <= start:
                    self.report(ctx, "video/clips", "endOffset must be after startOffset.", clip, "endOffset")
            elif clip.has("startOffset"):
                self.report(ctx, "video/clips", "startOffset must be a number of seconds.", clip, "startOffset")
        for action in ctx.items_of(item, "potentialAction"):
            if ctx.is_a(action, "SeekToAction"):
                target = " ".join(action.texts("target"))
                if "{seek_to_second_number}" not in target:
                    self.report(
                        ctx,
                        "video/clips",
                        'SeekToAction target must contain "{seek_to_second_number}".',
                        action,
                        "target",
                    )
                spec = " ".join(action.texts("startOffset-input"))
                if spec.strip() != "required name=seek_to_second_number":
                    self.report(
                        ctx,
                        "video/clips",
                        'SeekToAction needs "startOffset-input": "required name=seek_to_second_number".',
                        action,
                    )
        for event in ctx.items_of(item, "publication"):
            if not ctx.is_a(event, "BroadcastEvent"):
                continue
            live = event.first("isLiveBroadcast")
            if live not in (True, "true", "True"):
                self.report(ctx, "video/live", "The BroadcastEvent needs isLiveBroadcast: true.", event)
            if not event.has("startDate"):
                self.report(ctx, "video/live", "The BroadcastEvent needs startDate.", event)
        for stat in ctx.items_of(item, "interactionStatistic"):
            if not stat.has("userInteractionCount"):
                self.report(ctx, "google/recommended", "interactionStatistic needs userInteractionCount.", stat)


VIDEO = Video()
