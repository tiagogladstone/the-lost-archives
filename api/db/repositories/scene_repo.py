from __future__ import annotations

from typing import Optional

from api.db.client import get_supabase


def create_scene(data: dict) -> dict:
    res = get_supabase().table("scenes").insert(data).execute()
    return res.data[0]


def create_scenes_bulk(scenes: list[dict]) -> list[dict]:
    res = get_supabase().table("scenes").insert(scenes).execute()
    return res.data


def get_scene(scene_id: str) -> Optional[dict]:
    res = get_supabase().table("scenes").select("*").eq("id", scene_id).single().execute()
    return res.data if res.data else None


def get_scenes_by_story(story_id: str) -> list[dict]:
    res = (
        get_supabase()
        .table("scenes")
        .select("*")
        .eq("story_id", story_id)
        .order("scene_order")
        .execute()
    )
    return res.data


def update_scene(scene_id: str, data: dict) -> dict:
    res = get_supabase().table("scenes").update(data).eq("id", scene_id).execute()
    return res.data[0] if res.data else {}
