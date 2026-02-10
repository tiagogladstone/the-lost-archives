from __future__ import annotations

import base64
import logging
import subprocess
import tempfile
import os

import requests
import yaml

from api.config import GOOGLE_API_KEY, VOICES
from api.services.storage import upload_file
from api.db.repositories import story_repo, scene_repo

logger = logging.getLogger(__name__)

TTS_URL = "https://texttospeech.googleapis.com/v1/text:synthesize"
TTS_CHAR_LIMIT = 5000


def _get_audio_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _chunk_text(text: str, limit: int = TTS_CHAR_LIMIT) -> list[str]:
    """Split text into chunks under the TTS character limit."""
    if len(text) <= limit:
        return [text]

    chunks = []
    sentences = text.replace(". ", ".\n").split("\n")
    current = ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > limit:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence
    if current:
        chunks.append(current.strip())
    return chunks


def _synthesize_chunk(text: str, voice_name: str, language_code: str) -> bytes:
    payload = {
        "input": {"text": text},
        "voice": {
            "languageCode": language_code,
            "name": voice_name,
            "ssmlGender": "MALE",
        },
        "audioConfig": {"audioEncoding": "MP3"},
    }
    response = requests.post(f"{TTS_URL}?key={GOOGLE_API_KEY}", json=payload)
    response.raise_for_status()
    audio_b64 = response.json().get("audioContent")
    if not audio_b64:
        raise RuntimeError("TTS returned no audio content")
    return base64.b64decode(audio_b64)


async def generate_audio_for_scene(scene_id: str, story: dict) -> str:
    scene = scene_repo.get_scene(scene_id)
    if not scene:
        raise ValueError(f"Scene {scene_id} not found")

    language = story.get("languages", ["en-US"])[0]
    voice_info = VOICES.get(language)
    if not voice_info:
        raise ValueError(f"Language '{language}' not in voices config")

    voice_name = voice_info["voice_name"]
    language_code = voice_info["language_code"]
    text = scene["text_content"]

    # Chunk text if needed (TTS limit = 5000 chars)
    chunks = _chunk_text(text)
    audio_parts = []
    for chunk in chunks:
        audio_parts.append(_synthesize_chunk(chunk, voice_name, language_code))

    # Combine audio parts
    if len(audio_parts) == 1:
        audio_data = audio_parts[0]
    else:
        # Concatenate via ffmpeg
        with tempfile.TemporaryDirectory() as tmpdir:
            file_list_path = os.path.join(tmpdir, "files.txt")
            part_paths = []
            for i, part in enumerate(audio_parts):
                part_path = os.path.join(tmpdir, f"part_{i}.mp3")
                with open(part_path, "wb") as f:
                    f.write(part)
                part_paths.append(part_path)

            with open(file_list_path, "w") as f:
                for p in part_paths:
                    f.write(f"file '{p}'\n")

            combined_path = os.path.join(tmpdir, "combined.mp3")
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list_path, "-c", "copy", combined_path],
                check=True, capture_output=True,
            )
            with open(combined_path, "rb") as f:
                audio_data = f.read()

    # Get duration
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_data)
        tmp.flush()
        duration = _get_audio_duration(tmp.name)
        tmp_path = tmp.name

    try:
        # Upload
        storage_path = f"{story['id']}/{scene_id}.mp3"
        audio_url = upload_file("audio", storage_path, audio_data, "audio/mpeg")
    finally:
        os.unlink(tmp_path)

    # Update scene
    scene_repo.update_scene(scene_id, {"audio_url": audio_url, "duration_seconds": duration})
    logger.info(f"Scene {scene_id}: audio generated ({duration:.1f}s)")
    return audio_url


async def generate_audio_for_story(story_id: str) -> int:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    scenes = scene_repo.get_scenes_by_story(story_id)
    count = 0
    for scene in scenes:
        if not scene.get("audio_url"):
            await generate_audio_for_scene(scene["id"], story)
            count += 1

    logger.info(f"Generated {count} audio files for story {story_id}")
    return count
