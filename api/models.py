from pydantic import BaseModel, Field
from typing import List, Optional
import uuid

# --- Request Models ---

class CreateStoryRequest(BaseModel):
    topic: str
    description: str
    target_duration_minutes: int = Field(..., gt=0)
    languages: List[str] = ['en-US']

class SelectTitleRequest(BaseModel):
    title_option_id: uuid.UUID

class SelectThumbnailRequest(BaseModel):
    thumbnail_option_id: uuid.UUID

class ThumbnailFeedbackRequest(BaseModel):
    feedback: str

# --- Response Models ---

class StoryResponse(BaseModel):
    id: uuid.UUID
    topic: str
    status: str
    created_at: str
    updated_at: str

class SceneResponse(BaseModel):
    id: uuid.UUID
    scene_order: int
    text_content: str
    image_url: Optional[str] = None
    audio_url: Optional[str] = None
    duration_seconds: Optional[float] = None

class TitleOptionResponse(BaseModel):
    id: uuid.UUID
    title_text: str

class ThumbnailOptionResponse(BaseModel):
    id: uuid.UUID
    image_url: str
    version: int

class StoryDetailResponse(StoryResponse):
    script_text: Optional[str] = None
    scenes: List[SceneResponse] = []
    title_options: List[TitleOptionResponse] = []
    thumbnail_options: List[ThumbnailOptionResponse] = []
    selected_title: Optional[str] = None
    selected_thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    youtube_url: Optional[str] = None
    error_message: Optional[str] = None

class ReviewDataResponse(BaseModel):
    story_id: uuid.UUID
    video_url: Optional[str] = None
    title_options: List[TitleOptionResponse] = []
    thumbnail_options: List[ThumbnailOptionResponse] = []
    metadata: dict # description, tags

class PublishStatusResponse(BaseModel):
    status: str
    message: str

class JobResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    status: str
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
