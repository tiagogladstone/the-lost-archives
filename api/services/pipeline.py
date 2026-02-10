from __future__ import annotations

import asyncio
import logging
import traceback

from api.db.repositories import story_repo, scene_repo
from api.services import script as script_service
from api.services import image as image_service
from api.services import audio as audio_service
from api.services import translation as translation_service
from api.services import render as render_service
from api.services import thumbnail as thumbnail_service
from api.services import metadata as metadata_service
from api.services import upload as upload_service

logger = logging.getLogger(__name__)


async def run_pipeline(story_id: str) -> None:
    """Full pipeline: script → production → render → post_production → ready_for_review."""
    try:
        story = story_repo.get_story(story_id)
        if not story:
            raise ValueError(f"Story {story_id} not found")

        # ── Fase 1: Script (sequencial) ──────────────────────────
        story_repo.update_status(story_id, "scripting")
        scenes_count = await script_service.generate_script(story_id)
        logger.info(f"Pipeline [{story_id}]: script done, {scenes_count} scenes")

        # Reload story and scenes
        story = story_repo.get_story(story_id)
        scenes = scene_repo.get_scenes_by_story(story_id)

        # ── Fase 2: Production (paralelo por cena) ───────────────
        story_repo.update_status(story_id, "producing")

        tasks = []
        for scene in scenes:
            tasks.append(image_service.generate_image_for_scene(scene["id"], story))
            tasks.append(audio_service.generate_audio_for_scene(scene["id"], story))

        # Translation in parallel if multi-language
        languages = story.get("languages", ["en-US"])
        if len(languages) > 1:
            for scene in scenes:
                tasks.append(
                    translation_service.translate_scene(
                        scene["id"], languages[0], languages[1:]
                    )
                )

        await asyncio.gather(*tasks)
        logger.info(f"Pipeline [{story_id}]: production done")

        # ── Fase 2b: Render (needs all images + audio ready) ─────
        story_repo.update_status(story_id, "rendering")
        video_url = await render_service.render_video(story_id)
        logger.info(f"Pipeline [{story_id}]: render done → {video_url}")

        # ── Fase 3: Post-production (paralelo) ───────────────────
        story_repo.update_status(story_id, "post_production")
        await asyncio.gather(
            thumbnail_service.generate_thumbnails(story_id),
            metadata_service.generate_metadata(story_id),
        )
        logger.info(f"Pipeline [{story_id}]: post-production done")

        # ── Pausa: espera revisão humana ──────────────────────────
        story_repo.update_status(story_id, "ready_for_review")
        logger.info(f"Pipeline [{story_id}]: ready for review")

    except Exception as e:
        logger.error(f"Pipeline [{story_id}] FAILED: {e}\n{traceback.format_exc()}")
        story_repo.update_status(story_id, "failed", error_message=str(e))


async def publish(story_id: str) -> None:
    """Publish to YouTube (called after human review)."""
    try:
        story_repo.update_status(story_id, "publishing")
        youtube_url = await upload_service.upload_to_youtube(story_id)
        story_repo.update_status(story_id, "published")
        logger.info(f"Pipeline [{story_id}]: published → {youtube_url}")

    except Exception as e:
        logger.error(f"Publish [{story_id}] FAILED: {e}\n{traceback.format_exc()}")
        story_repo.update_status(story_id, "failed", error_message=str(e))
