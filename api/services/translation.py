from __future__ import annotations

import logging

import google.generativeai as genai

from api.config import GOOGLE_API_KEY
from api.db.repositories import story_repo, scene_repo

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


async def translate_scene(scene_id: str, source_language: str, target_languages: list[str]) -> dict:
    scene = scene_repo.get_scene(scene_id)
    if not scene:
        raise ValueError(f"Scene {scene_id} not found")

    text = scene["text_content"]
    translated = scene.get("translated_text") or {}
    if not isinstance(translated, dict):
        translated = {}

    model = genai.GenerativeModel("gemini-2.0-flash")

    for lang in target_languages:
        if lang in translated and translated[lang]:
            logger.info(f"Scene {scene_id}: translation to '{lang}' already exists, skipping")
            continue

        response = model.generate_content(
            f"""Translate the following text from {source_language} to {lang}.
Do not add any extra text, formatting, or explanations. Only output the translated text.

Text to translate:
"{text}"
"""
        )
        if response.text and response.text.strip():
            translated[lang] = response.text.strip()
            logger.info(f"Scene {scene_id}: translated to '{lang}'")
        else:
            logger.warning(f"Scene {scene_id}: empty translation for '{lang}'")

    scene_repo.update_scene(scene_id, {"translated_text": translated})
    return translated


async def translate_story(story_id: str) -> int:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    languages = story.get("languages", ["en-US"])
    if len(languages) < 2:
        logger.info(f"Story {story_id}: only one language, skipping translation")
        return 0

    source = languages[0]
    targets = languages[1:]
    scenes = scene_repo.get_scenes_by_story(story_id)

    count = 0
    for scene in scenes:
        await translate_scene(scene["id"], source, targets)
        count += 1

    logger.info(f"Translated {count} scenes for story {story_id}")
    return count
