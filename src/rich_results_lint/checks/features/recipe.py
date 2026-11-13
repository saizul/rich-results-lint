"""Recipe, with HowToStep and HowToSection instructions."""

from __future__ import annotations

import re

from ...model import Item
from ..base import Context
from .base import Feature
from .review import REVIEW_SNIPPET

_STEP_LABEL = re.compile(r"^\s*(?:step\s*\d+|directions?|instructions?)\s*[:.)-]", re.I)


class Recipe(Feature):
    id = "recipe"
    name = "Recipe"
    doc = "recipe"
    types = ("Recipe",)
    required = ("image", "name")
    recommended = (
        "aggregateRating",
        "author",
        "cookTime|totalTime",
        "datePublished",
        "description",
        "keywords",
        "nutrition.calories",
        "prepTime|totalTime",
        "recipeCategory",
        "recipeCuisine",
        "recipeIngredient",
        "recipeInstructions",
        "recipeYield",
        "video",
    )

    def extra(self, ctx: Context, item: Item) -> None:
        if item.has("cookTime") and not item.has("prepTime"):
            self.report(
                ctx,
                "recipe/times",
                "cookTime is set without prepTime; Google needs both, or totalTime.",
                item,
                "cookTime",
            )
        if ctx.present(item, "nutrition.calories") and not item.has("recipeYield"):
            self.report(
                ctx,
                "recipe/yield",
                "recipeYield (servings) is required when nutrition.calories is set.",
                item,
                "nutrition",
            )
        if item.has("ingredients") and not item.has("recipeIngredient"):
            self.report(
                ctx, "recipe/instructions", 'Use "recipeIngredient"; "ingredients" is superseded.', item, "ingredients"
            )
        instructions = item.get("recipeInstructions")
        texts = [v for v in instructions if isinstance(v, str)]
        if texts and len(instructions) == 1 and len(texts[0]) > 200:
            self.report(
                ctx,
                "recipe/instructions",
                "recipeInstructions is one block of text; use a list of HowToStep items so Google can show the steps.",
                item,
                "recipeInstructions",
            )
        for value in instructions:
            node = ctx.resolve(value)
            if isinstance(node, Item):
                self.check_instruction(ctx, node)
            elif isinstance(node, str) and _STEP_LABEL.match(node):
                self.report(
                    ctx,
                    "recipe/instructions",
                    f'Remove labels such as "Step 1" from the instruction text: "{node[:40]}".',
                    item,
                    "recipeInstructions",
                )
        REVIEW_SNIPPET.check_nested(ctx, item)

    def check_instruction(self, ctx: Context, node: Item) -> None:
        if ctx.is_a(node, "HowToSection"):
            if not node.has("name"):
                self.report(ctx, "recipe/instructions", "The HowToSection needs a name.", node)
            steps = ctx.items_of(node, "itemListElement")
            if not steps:
                self.report(ctx, "recipe/instructions", "The HowToSection needs itemListElement steps.", node)
            for step in steps:
                self.check_instruction(ctx, step)
            return
        if ctx.is_a(node, "HowToStep"):
            if not (node.has("text") or node.has("itemListElement")):
                self.report(
                    ctx,
                    "recipe/instructions",
                    "The HowToStep needs text (or itemListElement with HowToDirection/HowToTip).",
                    node,
                )
            for text in node.texts("text"):
                if _STEP_LABEL.match(text):
                    self.report(
                        ctx,
                        "recipe/instructions",
                        f'Remove labels such as "Step 1" from the step text: "{text[:40]}".',
                        node,
                        "text",
                    )
            for name in node.texts("name"):
                if re.fullmatch(r"\s*(?:step\s*)?\d+\s*", name, re.I):
                    self.report(
                        ctx,
                        "recipe/instructions",
                        f'HowToStep name "{name}" is a step number; use a short phrase or leave it out.',
                        node,
                        "name",
                    )
            for sub in ctx.items_of(node, "itemListElement"):
                if not sub.has("text"):
                    self.report(ctx, "recipe/instructions", f"The {sub.label()} needs text.", sub)
            return
        if node.types:
            self.report(
                ctx,
                "recipe/instructions",
                f"recipeInstructions holds a {node.label()}; use HowToStep or HowToSection.",
                node,
            )


RECIPE = Recipe()
