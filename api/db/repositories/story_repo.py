from __future__ import annotations

import logging
from typing import Optional

from api.db.client import get_supabase

logger = logging.getLogger(__name__)


def create_story(data: dict) -> dict:
    res = get_supabase().table("stories").insert(data).execute()
    return res.data[0]


def get_story(story_id: str) -> Optional[dict]:
    res = get_supabase().table("stories").select("*").eq("id", story_id).single().execute()
    return res.data if res.data else None


def list_stories(status: Optional[str] = None, limit: int = 20, offset: int = 0) -> list[dict]:
    query = get_supabase().table("stories").select(
        "id, topic, status, style, aspect_ratio, created_at, updated_at"
    ).order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    query = query.limit(limit).offset(offset)
    return query.execute().data


def update_story(story_id: str, data: dict) -> dict:
    res = get_supabase().table("stories").update(data).eq("id", story_id).execute()
    return res.data[0] if res.data else {}


def delete_story(story_id: str) -> None:
    get_supabase().table("stories").delete().eq("id", story_id).execute()


def update_status(story_id: str, status: str, error_message: str | None = None) -> None:
    data: dict = {"status": status}
    if error_message is not None:
        data["error_message"] = error_message
    get_supabase().table("stories").update(data).eq("id", story_id).execute()
    logger.info(f"Story {story_id} → {status}")
