from __future__ import annotations

import logging
import os
import tempfile
import uuid

import google.generativeai as genai
from google.genai import Client
from google.genai.types import GenerateImagesConfig

from api.config import GOOGLE_API_KEY
from api.services.storage import upload_file
from api.db.repositories import story_repo, options_repo

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)
_imagen_client = Client(api_key=GOOGLE_API_KEY)


def _generate_thumbnail_prompts(topic: str, script_text: str, style: str) -> list[str]:
    model = genai.GenerativeModel("gemini-2.0-flash")

    system_prompt = f"""You are an expert in creating viral YouTube thumbnails. Generate 3 distinct, compelling thumbnail prompts based on the video's topic and script.

Visual style preference: {style}

Instructions:
1. Analyze the topic and script for key themes and emotional hooks.
2. Think visually: bold colors, high contrast, clear subjects.
3. Suggest short overlay text (2-5 words) for curiosity.
4. Create 3 DIVERSE options:
   - Option 1 (Symbolic/Abstract): A powerful metaphor or symbol.
   - Option 2 (Action/Climax): A key event or conflict.
   - Option 3 (Human/Emotional): A human figure's reaction.
5. Return ONLY 3 lines, one prompt per line. No numbering, no explanations."""

    prompt = f"Topic: {topic}\nScript:\n{script_text[:1500]}"
    response = model.generate_content(
        [system_prompt, prompt],
        generation_config=genai.types.GenerationConfig(temperature=0.9, max_output_tokens=1024),
    )

    prompts = [p.strip() for p in response.text.split("\n") if p.strip()]
    if len(prompts) < 3:
        raise RuntimeError(f"Expected 3 thumbnail prompts, got {len(prompts)}")
    return prompts[:3]


async def generate_thumbnails(story_id: str) -> int:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    topic = story["topic"]
    script_text = story.get("script_text", "")
    style = story.get("style", "cinematic")

    prompts = _generate_thumbnail_prompts(topic, script_text, style)

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, prompt in enumerate(prompts):
            logger.info(f"Generating thumbnail {i+1}/3 for story {story_id}")

            image_response = _imagen_client.models.generate_images(
                model="imagen-4.0-generate-001",
                prompt=prompt,
                config=GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio="16:9",
                    output_mime_type="image/png",
                ),
            )

            if not image_response.generated_images:
                logger.warning(f"Thumbnail {i+1}: no image returned")
                continue

            filename = f"thumb_{uuid.uuid4()}.png"
            local_path = os.path.join(tmpdir, filename)
            image_response.generated_images[0].image.save(local_path)

            with open(local_path, "rb") as f:
                storage_path = f"{story_id}/{filename}"
                image_url = upload_file("thumbnails", storage_path, f.read(), "image/png")

            options_repo.create_thumbnail_option({
                "story_id": story_id,
                "image_url": image_url,
                "prompt": prompt,
            })
            logger.info(f"Thumbnail {i+1} uploaded: {image_url}")

    return 3
