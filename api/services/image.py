from __future__ import annotations

import logging
import tempfile
import os

import google.generativeai as genai
from google.genai import Client
from google.genai.types import GenerateImagesConfig

from api.config import GOOGLE_API_KEY
from api.services.storage import upload_file
from api.db.repositories import story_repo, scene_repo

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)
_imagen_client = Client(api_key=GOOGLE_API_KEY)

ASPECT_RATIOS = {"16:9": "16:9", "9:16": "9:16"}
STYLE_MODIFIERS = {
    "cinematic": "cinematic, photorealistic, dramatic lighting, film grain",
    "anime": "anime style, vibrant colors, detailed illustration",
    "realistic": "hyperrealistic, photograph, 8k resolution, detailed",
    "3d": "3D rendered, Pixar style, detailed textures, volumetric lighting",
}


async def generate_image_for_scene(scene_id: str, story: dict) -> str:
    scene = scene_repo.get_scene(scene_id)
    if not scene:
        raise ValueError(f"Scene {scene_id} not found")

    style = story.get("style", "cinematic")
    aspect_ratio = story.get("aspect_ratio", "16:9")
    style_mod = STYLE_MODIFIERS.get(style, STYLE_MODIFIERS["cinematic"])

    # Generate detailed image prompt via Gemini
    prompt_model = genai.GenerativeModel("gemini-2.0-flash")
    prompt_response = prompt_model.generate_content(
        f"""Based on the following narration text from a historical documentary, create a single, detailed prompt for an AI image generator.
The image should be {style_mod} and capture the mood of the scene.
Avoid text, logos, or watermarks. Specify camera angles, lighting, and composition.

Narration Text: "{scene['text_content']}"

Image Prompt:"""
    )
    image_prompt = prompt_response.text.strip()
    logger.info(f"Scene {scene_id}: image prompt generated")

    # Generate image via Imagen 4
    image_response = _imagen_client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=image_prompt,
        config=GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio=ASPECT_RATIOS.get(aspect_ratio, "16:9"),
            output_mime_type="image/png",
        ),
    )

    if not image_response.generated_images:
        raise RuntimeError(f"Imagen returned no images for scene {scene_id}")

    # Save to temp, upload to storage
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        image_response.generated_images[0].image.save(tmp.name)
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            storage_path = f"{story['id']}/{scene_id}.png"
            image_url = upload_file("images", storage_path, f.read(), "image/png")
    finally:
        os.unlink(tmp_path)

    # Update scene
    scene_repo.update_scene(scene_id, {"image_url": image_url, "image_prompt": image_prompt})
    logger.info(f"Scene {scene_id}: image uploaded")
    return image_url


async def generate_images_for_story(story_id: str) -> int:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    scenes = scene_repo.get_scenes_by_story(story_id)
    count = 0
    for scene in scenes:
        if not scene.get("image_url"):
            await generate_image_for_scene(scene["id"], story)
            count += 1

    logger.info(f"Generated {count} images for story {story_id}")
    return count
