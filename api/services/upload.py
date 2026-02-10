from __future__ import annotations

import base64
import json
import logging
import os
import tempfile
import urllib.request

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from api.config import YOUTUBE_TOKEN_JSON
from api.db.repositories import story_repo

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_youtube_service():
    creds = None

    # Option 1: Environment variable (base64 encoded)
    if YOUTUBE_TOKEN_JSON:
        try:
            token_json = base64.b64decode(YOUTUBE_TOKEN_JSON).decode("utf-8")
            token_data = json.loads(token_json)
            creds = Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri"),
                client_id=token_data.get("client_id"),
                client_secret=token_data.get("client_secret"),
                scopes=token_data.get("scopes", SCOPES),
            )
            logger.info("Using YouTube credentials from env var")
        except Exception as e:
            logger.warning(f"Failed to load credentials from env: {e}")

    # Option 2: youtube_token.json file
    if not creds and os.path.exists("youtube_token.json"):
        creds = Credentials.from_authorized_user_file("youtube_token.json", SCOPES)
        logger.info("Using YouTube credentials from youtube_token.json")

    if not creds:
        raise ValueError("No YouTube credentials found. Set YOUTUBE_TOKEN_JSON or provide youtube_token.json")

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        logger.info("Refreshed YouTube access token")

    return build("youtube", "v3", credentials=creds)


def _upload_video(youtube, video_path: str, title: str, description: str, tags: str, privacy: str = "unlisted") -> str:
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags.split(",") if isinstance(tags, str) else tags,
            "categoryId": "22",  # People & Blogs
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )
    response = request.execute()
    video_id = response["id"]
    logger.info(f"Video uploaded: https://youtu.be/{video_id}")
    return video_id


def _upload_thumbnail(youtube, video_id: str, thumbnail_path: str) -> None:
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumbnail_path),
    ).execute()
    logger.info(f"Thumbnail uploaded for video {video_id}")


async def upload_to_youtube(story_id: str) -> str:
    story = story_repo.get_story(story_id)
    if not story:
        raise ValueError(f"Story {story_id} not found")

    # Validate required fields
    for field in ["selected_title", "selected_thumbnail_url", "video_url", "metadata"]:
        if not story.get(field):
            raise ValueError(f"Story missing '{field}' for upload")

    metadata = story["metadata"]
    if not metadata.get("description") or not metadata.get("tags"):
        raise ValueError("Story metadata incomplete (missing description or tags)")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Download video
        video_path = os.path.join(tmpdir, "video.mp4")
        urllib.request.urlretrieve(story["video_url"], video_path)

        # Download thumbnail
        thumb_path = os.path.join(tmpdir, "thumbnail.png")
        urllib.request.urlretrieve(story["selected_thumbnail_url"], thumb_path)

        # Upload
        youtube = _get_youtube_service()
        video_id = _upload_video(
            youtube,
            video_path,
            title=story["selected_title"],
            description=metadata["description"],
            tags=metadata["tags"],
            privacy="unlisted",
        )
        _upload_thumbnail(youtube, video_id, thumb_path)

    # Update story
    youtube_url = f"https://youtu.be/{video_id}"
    story_repo.update_story(story_id, {
        "youtube_url": youtube_url,
        "youtube_video_id": video_id,
    })

    logger.info(f"Story {story_id} published: {youtube_url}")
    return youtube_url
