from enum import Enum


class StoryStatus(str, Enum):
    DRAFT = "draft"
    SCRIPTING = "scripting"
    PRODUCING = "producing"
    RENDERING = "rendering"
    POST_PRODUCTION = "post_production"
    READY_FOR_REVIEW = "ready_for_review"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
