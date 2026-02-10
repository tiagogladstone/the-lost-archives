from __future__ import annotations

import itertools
import json
import logging
import os
import shutil
import subprocess
import tempfile

from api.services.storage import upload_file, download_to_temp
from api.db.repositories import story_repo, scene_repo

logger = logging.getLogger(__name__)

EFFECTS = ["zoom_in", "pan_right", "zoom_out", "pan_left"]


def _get_media_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def _apply_ken_burns(input_path: str, output_path: str, duration: float, effect: str, resolution: str) -> None:
    w, h = map(int, resolution.split("x"))
    total_frames = int(duration * 25)

    vf_options = {
        "zoom_in": f"zoompan=z='min(zoom+0.0015,1.5)':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}",
        "zoom_out": f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={total_frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}",
        "pan_left": f"zoompan=z=1.2:d=1:x='iw/2-(iw/zoom/2)-(iw*t)/(2*({duration}))':y='ih/2-(ih/zoom/2)':s={w}x{h}",
        "pan_right": f"zoompan=z=1.2:d=1:x='iw/2-(iw/zoom/2)+(iw*t)/(2*({duration}))':y='ih/2-(ih/zoom/2)':s={w}x{h}",
    }

    vf = vf_options[effect]
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"scale={w}:-1,crop={w}:{h},{vf}",
        "-c:v", "libx264",
        "-t", str(duration),
        "-pix_fmt", "yuv420p",
        "-preset", "veryfast",
        "-crf", "22",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _get_resolution(aspect_ratio: str) -> str:
    if aspect_ratio == "9:16":
        return "1080x1920"
    return "1920x1080"


async def render_video(story_id: str) -> str:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    scenes = scene_repo.get_scenes_by_story(story_id)
    if not scenes:
        raise ValueError(f"No scenes found for story {story_id}")

    resolution = _get_resolution(story.get("aspect_ratio", "16:9"))

    with tempfile.TemporaryDirectory() as tmpdir:
        images_dir = os.path.join(tmpdir, "images")
        audio_dir = os.path.join(tmpdir, "audio")
        clips_dir = os.path.join(tmpdir, "clips")
        os.makedirs(images_dir)
        os.makedirs(audio_dir)
        os.makedirs(clips_dir)

        # Download all assets
        image_paths = []
        audio_paths = []
        for i, scene in enumerate(scenes):
            if not scene.get("image_url") or not scene.get("audio_url"):
                raise ValueError(f"Scene {scene['id']} missing image_url or audio_url")

            img_path = os.path.join(images_dir, f"scene_{i:03d}.png")
            aud_path = os.path.join(audio_dir, f"scene_{i:03d}.mp3")

            # Download
            import urllib.request
            urllib.request.urlretrieve(scene["image_url"], img_path)
            urllib.request.urlretrieve(scene["audio_url"], aud_path)

            image_paths.append(img_path)
            audio_paths.append(aud_path)

        # Concatenate all audio
        narration_path = os.path.join(tmpdir, "narration.mp3")
        file_list = os.path.join(tmpdir, "audio_files.txt")
        with open(file_list, "w") as f:
            for p in audio_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", narration_path],
            check=True, capture_output=True, text=True,
        )

        narration_duration = _get_media_duration(narration_path)
        clip_duration = narration_duration / len(image_paths)

        # Apply Ken Burns to each image
        effect_cycle = itertools.cycle(EFFECTS)
        processed_clips = []
        for i, img_path in enumerate(image_paths):
            effect = next(effect_cycle)
            clip_path = os.path.join(clips_dir, f"clip_{i:03d}.mp4")
            _apply_ken_burns(img_path, clip_path, clip_duration, effect, resolution)
            processed_clips.append(clip_path)

        if not processed_clips:
            raise RuntimeError("No clips were processed")

        # Concatenate clips + audio
        clips_list = os.path.join(tmpdir, "clips_list.txt")
        with open(clips_list, "w") as f:
            for p in processed_clips:
                f.write(f"file '{os.path.abspath(p)}'\n")

        final_path = os.path.join(tmpdir, f"{story_id}.mp4")
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", clips_list,
            "-i", narration_path,
            "-filter_complex", "[0:v]setsar=1[v];[1:a]volume=1.0[a_out]",
            "-map", "[v]",
            "-map", "[a_out]",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(narration_duration),
            final_path,
        ]
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

        # Upload
        with open(final_path, "rb") as f:
            storage_path = f"{story_id}/{story_id}.mp4"
            video_url = upload_file("videos", storage_path, f.read(), "video/mp4")

    # Update story
    story_repo.update_story(story_id, {"video_url": video_url})
    logger.info(f"Video rendered and uploaded for story {story_id}")
    return video_url
