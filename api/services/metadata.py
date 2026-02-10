from __future__ import annotations

import json
import logging

import google.generativeai as genai

from api.config import GOOGLE_API_KEY
from api.db.repositories import story_repo, options_repo

logger = logging.getLogger(__name__)

genai.configure(api_key=GOOGLE_API_KEY)


async def generate_metadata(story_id: str) -> int:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    topic = story["topic"]
    script_text = story.get("script_text", "")

    model = genai.GenerativeModel("gemini-2.0-flash")

    system_prompt = """You are a world-class YouTube SEO and content strategist. Generate viral, SEO-optimized metadata for a video.

Instructions:
1. Generate 3 SEO-optimized, catchy titles that create curiosity.
2. Write a compelling description (1200-1500 chars) with:
   - Strong hook summarizing the video's core question
   - Naturally woven keywords
   - Logical sections with timestamps (invent plausible ones)
   - Call to action at the end
3. Generate relevant tags as a comma-separated string (max 490 chars).
4. Return ONLY a valid JSON object:
   {
     "titles": ["title 1", "title 2", "title 3"],
     "description": "full description...",
     "tags": "tag1,tag2,tag3"
   }

No markdown, no explanations. Raw JSON only."""

    prompt = f"Topic: {topic}\nScript:\n{script_text[:4000]}"
    response = model.generate_content(
        [system_prompt, prompt],
        generation_config=genai.types.GenerationConfig(
            temperature=0.8,
            max_output_tokens=4096,
            response_mime_type="application/json",
        ),
    )

    metadata = json.loads(response.text)

    # Validate
    if not all(k in metadata for k in ["titles", "description", "tags"]):
        raise ValueError(f"Metadata missing required fields: {metadata}")
    if len(metadata["titles"]) < 3:
        raise ValueError(f"Expected 3 titles, got {len(metadata['titles'])}")

    # Save title options
    title_records = [{"story_id": story_id, "title_text": t} for t in metadata["titles"][:3]]
    options_repo.create_title_options(title_records)

    # Save description and tags to story metadata
    story_repo.update_story(story_id, {
        "metadata": {
            "description": metadata["description"],
            "tags": metadata["tags"],
        }
    })

    logger.info(f"Metadata generated for story {story_id}: 3 titles + description + tags")
    return 3
