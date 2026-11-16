"""Profile page (ProfilePage) and Discussion forum (DiscussionForumPosting)."""

from __future__ import annotations

from ...model import Item
from ...values import as_datetime
from ...vocab import local_name
from ..base import Context
from .base import Feature

_INTERACTIONS = {
    "FollowAction",
    "LikeAction",
    "WriteAction",
    "ShareAction",
    "BefriendAction",
    "CommentAction",
    "DislikeAction",
    "SubscribeAction",
    "VoteAction",
}


def check_interactions(feature: Feature, ctx: Context, item: Item, prop: str) -> None:
    for stat in ctx.items_of(item, prop):
        if not stat.has("userInteractionCount"):
            feature.report(ctx, "google/recommended", f"{prop} needs userInteractionCount.", stat)
        for kind in stat.texts("interactionType"):
            if local_name(kind) not in _INTERACTIONS:
                feature.report(
                    ctx,
                    "profile/interaction",
                    f'interactionType "{kind}" is not one Google reads (FollowAction, LikeAction, WriteAction ...).',
                    stat,
                    "interactionType",
                )
    for raw in item.get(prop):
        if not isinstance(ctx.resolve(raw), Item):
            feature.report(ctx, "profile/interaction", f"{prop} must be an InteractionCounter.", item, prop)


class ProfilePage(Feature):
    id = "profile-page"
    name = "Profile page"
    doc = "profile-page"
    types = ("ProfilePage",)
    required = ("mainEntity", "mainEntity.name|mainEntity.alternateName")
    recommended = ("dateCreated", "dateModified", "mainEntity.image", "mainEntity.description|mainEntity.sameAs")

    def extra(self, ctx: Context, item: Item) -> None:
        entities = ctx.items_of(item, "mainEntity")
        for value in item.get("mainEntity"):
            if isinstance(ctx.resolve(value), str):
                self.report(
                    ctx, "profile/main-entity", "mainEntity is text; use a Person or Organization.", item, "mainEntity"
                )
        if len(entities) > 1:
            self.report(ctx, "profile/main-entity", "A ProfilePage should describe one person or organization.", item)
        for entity in entities:
            if entity.types and not ctx.is_a(entity, "Person", "Organization"):
                self.report(
                    ctx,
                    "profile/main-entity",
                    f"mainEntity is a {entity.label()}; a profile page is about a Person or Organization.",
                    entity,
                )
            check_interactions(self, ctx, entity, "interactionStatistic")
            check_interactions(self, ctx, entity, "agentInteractionStatistic")
        created = next((as_datetime(s) for s in item.texts("dateCreated") if as_datetime(s)), None)
        modified = next((as_datetime(s) for s in item.texts("dateModified") if as_datetime(s)), None)
        if created and modified and modified < created:
            self.report(ctx, "profile/dates", "dateModified is before dateCreated.", item, "dateModified")


class DiscussionForum(Feature):
    id = "discussion-forum"
    name = "Discussion forum"
    doc = "discussion-forum"
    types = ("DiscussionForumPosting",)
    required = ("author", "author.name", "datePublished", "text|image|video")
    recommended = ("author.url", "headline", "url", "dateModified", "comment|interactionStatistic")

    def extra(self, ctx: Context, item: Item) -> None:
        self.check_post(ctx, item)
        for comment in ctx.items_of(item, "comment"):
            self.check_comment(ctx, comment, item, depth=1)

    def check_post(self, ctx: Context, post: Item) -> None:
        for value in post.get("author"):
            if isinstance(ctx.resolve(value), str):
                self.report(ctx, "forum/author", f'author "{value}" is text; use a Person with a name.', post, "author")
        published = next((as_datetime(s) for s in post.texts("datePublished") if as_datetime(s)), None)
        modified = next((as_datetime(s) for s in post.texts("dateModified") if as_datetime(s)), None)
        if published and published > ctx.now:
            self.report(ctx, "forum/dates", "datePublished is in the future.", post, "datePublished")
        if published and modified and modified < published:
            self.report(ctx, "forum/dates", "dateModified is before datePublished.", post, "dateModified")
        check_interactions(self, ctx, post, "interactionStatistic")

    def check_comment(self, ctx: Context, comment: Item, parent: Item, depth: int) -> None:
        if depth > 20:
            return
        self.check_paths(
            ctx, comment, ("author", "author.name", "datePublished", "text|image|video"), "google/required", "a Comment"
        )
        self.check_post(ctx, comment)
        parent_date = next((as_datetime(s) for s in parent.texts("datePublished") if as_datetime(s)), None)
        own = next((as_datetime(s) for s in comment.texts("datePublished") if as_datetime(s)), None)
        if parent_date and own and own < parent_date:
            self.report(ctx, "forum/dates", "A reply is dated before the post it answers.", comment, "datePublished")
        for child in ctx.items_of(comment, "comment"):
            self.check_comment(ctx, child, comment, depth + 1)


PROFILE_PAGE = ProfilePage()
DISCUSSION_FORUM = DiscussionForum()
