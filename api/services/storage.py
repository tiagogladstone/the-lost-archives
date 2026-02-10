from __future__ import annotations

import logging
import tempfile
import urllib.request
from pathlib import Path

from api.db.client import get_supabase

logger = logging.getLogger(__name__)

BUCKETS = ["images", "audio", "videos", "thumbnails"]


def upload_file(bucket: str, path: str, data: bytes, content_type: str) -> str:
    get_supabase().storage.from_(bucket).upload(
        path=path,
        file=data,
        file_options={"content-type": content_type},
    )
    url = get_supabase().storage.from_(bucket).get_public_url(path)
    logger.info(f"Uploaded {bucket}/{path}")
    return url


def get_public_url(bucket: str, path: str) -> str:
    return get_supabase().storage.from_(bucket).get_public_url(path)


def download_to_temp(url: str, suffix: str = "") -> str:
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    urllib.request.urlretrieve(url, tmp.name)
    tmp.close()
    return tmp.name


def delete_story_files(story_id: str) -> None:
    for bucket in BUCKETS:
        try:
            files = get_supabase().storage.from_(bucket).list(story_id)
            if files:
                paths = [f"{story_id}/{f['name']}" for f in files]
                get_supabase().storage.from_(bucket).remove(paths)
                logger.info(f"Deleted {len(paths)} files from {bucket}/{story_id}")
        except Exception as e:
            logger.warning(f"Failed to clean {bucket}/{story_id}: {e}")
