from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel


class SceneResponse(BaseModel):
    id: uuid.UUID
    story_id: uuid.UUID
    scene_order: int
    text_content: str
    translated_text: dict = {}
    image_prompt: Optional[str] = None
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None
