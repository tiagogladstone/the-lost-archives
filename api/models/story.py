from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, Field

from .enums import StoryStatus
from .scene import SceneResponse


class CreateStoryRequest(BaseModel):
    topic: str
    description: str = ""
    target_duration_minutes: int = Field(default=8, gt=0)
    languages: list[str] = Field(default=["en-US"])
    style: str = Field(default="cinematic", pattern="^(cinematic|anime|realistic|3d)$")
    aspect_ratio: str = Field(default="16:9", pattern="^(16:9|9:16)$")


class TitleOptionResponse(BaseModel):
    id: uuid.UUID
    title_text: str


class ThumbnailOptionResponse(BaseModel):
    id: uuid.UUID
    image_url: str
    prompt: Optional[str] = None


class StoryResponse(BaseModel):
    id: uuid.UUID
    topic: str
    status: StoryStatus
    style: str
    aspect_ratio: str
    created_at: str
    updated_at: str


class StoryDetailResponse(StoryResponse):
    description: Optional[str] = None
    target_duration_minutes: int = 8
    languages: list[str] = ["en-US"]
    script_text: Optional[str] = None
    scenes: list[SceneResponse] = []
    title_options: list[TitleOptionResponse] = []
    thumbnail_options: list[ThumbnailOptionResponse] = []
    selected_title: Optional[str] = None
    selected_thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    youtube_url: Optional[str] = None
    metadata: dict = {}
    error_message: Optional[str] = None
