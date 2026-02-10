from __future__ import annotations

import logging

import google.generativeai as genai

from api.config import GOOGLE_API_KEY
from api.db.repositories import story_repo, scene_repo

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


async def generate_script(story_id: str) -> int:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    topic = story["topic"]
    description = story.get("description", "")
    duration = story.get("target_duration_minutes", 8)
    style = story.get("style", "cinematic")

    logger.info(f"Generating script for story {story_id}: '{topic}'")

    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"""Write a compelling narration script for a YouTube video about: {topic}
Context: {description}
Target duration: {duration} minutes (approximately {duration * 150} words)
Visual style: {style}
Style: Documentary, engaging, mysterious

Write ONLY the narration text, divided into clear paragraphs.
Each paragraph will become a separate scene in the video.
Do not include any formatting like markdown, headers, or scene descriptions.
Just write the plain text of the narration.
Ensure paragraphs are separated by a double newline."""

    response = model.generate_content(prompt)

    if not response.text or not response.text.strip():
        raise RuntimeError("Gemini returned empty script")

    script_text = response.text.strip()
    logger.info(f"Generated script: {len(script_text)} chars")

    # Split into scenes (paragraphs)
    paragraphs = [p.strip() for p in script_text.split("\n\n") if p.strip()]
    if not paragraphs:
        raise RuntimeError("Script has no paragraphs after splitting")

    # Save script
    story_repo.update_story(story_id, {"script_text": script_text})

    # Create scenes
    scenes_data = [
        {
            "story_id": story_id,
            "scene_order": i + 1,
            "text_content": text,
        }
        for i, text in enumerate(paragraphs)
    ]
    scene_repo.create_scenes_bulk(scenes_data)

    logger.info(f"Created {len(paragraphs)} scenes for story {story_id}")
    return len(paragraphs)
