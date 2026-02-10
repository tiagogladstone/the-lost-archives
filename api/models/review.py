from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel

from .story import TitleOptionResponse, ThumbnailOptionResponse


class ReviewResponse(BaseModel):
    story_id: uuid.UUID
    video_url: Optional[str] = None
    title_options: list[TitleOptionResponse] = []
    thumbnail_options: list[ThumbnailOptionResponse] = []
    metadata: dict = {}


class SelectReviewRequest(BaseModel):
    title_option_id: uuid.UUID
    thumbnail_option_id: uuid.UUID


class PublishResponse(BaseModel):
    status: str
    message: str
