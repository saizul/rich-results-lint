"""Google rich result features."""

from __future__ import annotations

from .article import ARTICLE
from .base import Feature
from .breadcrumb import BREADCRUMB
from .deprecated import FAQ, HOWTO
from .event import EVENT
from .job_posting import JOB_POSTING
from .local_business import LOCAL_BUSINESS, ORGANIZATION
from .product import PRODUCT
from .recipe import RECIPE
from .review import REVIEW_SNIPPET
from .video import VIDEO

FEATURES: tuple[Feature, ...] = (
    ARTICLE,
    PRODUCT,
    BREADCRUMB,
    FAQ,
    HOWTO,
    LOCAL_BUSINESS,
    ORGANIZATION,
    EVENT,
    JOB_POSTING,
    RECIPE,
    VIDEO,
    REVIEW_SNIPPET,
)

FEATURES_BY_ID = {f.id: f for f in FEATURES}

__all__ = ["FEATURES", "FEATURES_BY_ID", "Feature"]
