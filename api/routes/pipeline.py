from __future__ import annotations

import logging
import traceback
import uuid

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import verify_api_key
from api.db.repositories import story_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"], dependencies=[Depends(verify_api_key)])


def _get_story_or_404(story_id: uuid.UUID) -> dict:
    story = story_repo.get_story(str(story_id))
    if not story:
        raise HTTPException(status_code=404, detail=f"Story {story_id} not found")
    return story


@router.post("/{story_id}/script")
async def run_script(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.script import generate_script
    result = await generate_script(str(story_id))
    return {"status": "ok", "scenes_created": result}


@router.post("/{story_id}/images")
async def run_images(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.image import generate_images_for_story
    count = await generate_images_for_story(str(story_id))
    return {"status": "ok", "images_generated": count}


@router.post("/{story_id}/audio")
async def run_audio(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.audio import generate_audio_for_story
    count = await generate_audio_for_story(str(story_id))
    return {"status": "ok", "audio_generated": count}


@router.post("/{story_id}/translate")
async def run_translate(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.translation import translate_story
    count = await translate_story(str(story_id))
    return {"status": "ok", "scenes_translated": count}


@router.post("/{story_id}/render")
async def run_render(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.render import render_video
    try:
        video_url = await render_video(str(story_id))
        return {"status": "ok", "video_url": video_url}
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"
        logger.error(f"Render [{story_id}] FAILED: {error_msg}\n{traceback.format_exc()}")
        story_repo.update_status(str(story_id), "failed", error_message=error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/{story_id}/thumbnails")
async def run_thumbnails(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.thumbnail import generate_thumbnails
    count = await generate_thumbnails(str(story_id))
    return {"status": "ok", "thumbnails_generated": count}


@router.post("/{story_id}/metadata")
async def run_metadata(story_id: uuid.UUID):
    _get_story_or_404(story_id)
    from api.services.metadata import generate_metadata
    result = await generate_metadata(str(story_id))
    return {"status": "ok", "titles_generated": result}
