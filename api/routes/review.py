from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from api.dependencies import verify_api_key
from api.models.review import ReviewResponse, SelectReviewRequest, PublishResponse
from api.db.repositories import story_repo, options_repo

router = APIRouter(prefix="/stories", tags=["review"], dependencies=[Depends(verify_api_key)])


@router.get("/{story_id}/review", response_model=ReviewResponse)
async def get_review(story_id: uuid.UUID):
    story = story_repo.get_story(str(story_id))
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story["status"] != "ready_for_review":
        raise HTTPException(
            status_code=400,
            detail=f"Story not ready for review. Current status: {story['status']}",
        )

    return {
        "story_id": story_id,
        "video_url": story.get("video_url"),
        "title_options": options_repo.get_title_options(str(story_id)),
        "thumbnail_options": options_repo.get_thumbnail_options(str(story_id)),
        "metadata": story.get("metadata", {}),
    }


@router.post("/{story_id}/review", response_model=ReviewResponse)
async def select_review(story_id: uuid.UUID, body: SelectReviewRequest):
    story = story_repo.get_story(str(story_id))
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story["status"] != "ready_for_review":
        raise HTTPException(
            status_code=400,
            detail=f"Story not ready for review. Current status: {story['status']}",
        )

    # Validate title option
    title_opt = options_repo.get_title_option(str(body.title_option_id), str(story_id))
    if not title_opt:
        raise HTTPException(status_code=404, detail="Title option not found for this story")

    # Validate thumbnail option
    thumb_opt = options_repo.get_thumbnail_option(str(body.thumbnail_option_id), str(story_id))
    if not thumb_opt:
        raise HTTPException(status_code=404, detail="Thumbnail option not found for this story")

    # Update story with selections
    story_repo.update_story(str(story_id), {
        "selected_title": title_opt["title_text"],
        "selected_thumbnail_url": thumb_opt["image_url"],
    })

    # Return updated review data
    return {
        "story_id": story_id,
        "video_url": story.get("video_url"),
        "title_options": options_repo.get_title_options(str(story_id)),
        "thumbnail_options": options_repo.get_thumbnail_options(str(story_id)),
        "metadata": story.get("metadata", {}),
    }


@router.post("/{story_id}/publish", response_model=PublishResponse, status_code=202)
async def publish(story_id: uuid.UUID, background_tasks: BackgroundTasks):
    story = story_repo.get_story(str(story_id))
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story["status"] != "ready_for_review":
        raise HTTPException(
            status_code=400,
            detail=f"Story not in publishable state. Current status: {story['status']}",
        )
    if not story.get("selected_title") or not story.get("selected_thumbnail_url"):
        raise HTTPException(
            status_code=400,
            detail="Title and thumbnail must be selected before publishing",
        )

    story_repo.update_status(str(story_id), "publishing")

    try:
        from api.services.pipeline import publish
        background_tasks.add_task(publish, str(story_id))
    except ImportError:
        pass  # Pipeline service not yet implemented

    return {"status": "publishing", "message": "Story queued for YouTube upload"}
