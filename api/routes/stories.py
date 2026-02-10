from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from typing import Optional

from api.dependencies import verify_api_key
from api.models.story import (
    CreateStoryRequest,
    StoryResponse,
    StoryDetailResponse,
    TitleOptionResponse,
    ThumbnailOptionResponse,
)
from api.models.scene import SceneResponse
from api.db.repositories import story_repo, scene_repo, options_repo

router = APIRouter(prefix="/stories", tags=["stories"], dependencies=[Depends(verify_api_key)])


def _get_story_or_404(story_id: uuid.UUID) -> dict:
    story = story_repo.get_story(str(story_id))
    if not story:
        raise HTTPException(status_code=404, detail=f"Story {story_id} not found")
    return story


@router.post("", response_model=StoryResponse, status_code=201)
async def create_story(body: CreateStoryRequest, background_tasks: BackgroundTasks):
    story = story_repo.create_story({
        "topic": body.topic,
        "description": body.description,
        "target_duration_minutes": body.target_duration_minutes,
        "languages": body.languages,
        "style": body.style,
        "aspect_ratio": body.aspect_ratio,
        "status": "draft",
    })

    # Import here to avoid circular imports; pipeline service is built in Fase 3
    try:
        from api.services.pipeline import run_pipeline
        background_tasks.add_task(run_pipeline, story["id"])
    except ImportError:
        pass  # Pipeline service not yet implemented

    return story


@router.get("", response_model=list[StoryResponse])
async def list_stories(
    status: Optional[str] = Query(None),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0),
):
    return story_repo.list_stories(status=status, limit=limit, offset=offset)


@router.get("/{story_id}", response_model=StoryDetailResponse)
async def get_story(story_id: uuid.UUID):
    story = _get_story_or_404(story_id)
    story["scenes"] = scene_repo.get_scenes_by_story(str(story_id))
    story["title_options"] = options_repo.get_title_options(str(story_id))
    story["thumbnail_options"] = options_repo.get_thumbnail_options(str(story_id))
    return story


@router.delete("/{story_id}", status_code=204)
async def delete_story(story_id: uuid.UUID):
    _get_story_or_404(story_id)

    # Clean up storage files
    try:
        from api.services.storage import delete_story_files
        delete_story_files(str(story_id))
    except (ImportError, Exception):
        pass  # Best-effort cleanup

    story_repo.delete_story(str(story_id))
