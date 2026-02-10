from __future__ import annotations

from typing import Optional

from api.db.client import get_supabase


# --- Title Options ---

def create_title_options(titles: list[dict]) -> list[dict]:
    res = get_supabase().table("title_options").insert(titles).execute()
    return res.data


def get_title_options(story_id: str) -> list[dict]:
    res = get_supabase().table("title_options").select("*").eq("story_id", story_id).execute()
    return res.data


def get_title_option(option_id: str, story_id: str) -> Optional[dict]:
    res = (
        get_supabase()
        .table("title_options")
        .select("*")
        .eq("id", option_id)
        .eq("story_id", story_id)
        .single()
        .execute()
    )
    return res.data if res.data else None


# --- Thumbnail Options ---

def create_thumbnail_option(data: dict) -> dict:
    res = get_supabase().table("thumbnail_options").insert(data).execute()
    return res.data[0]


def get_thumbnail_options(story_id: str) -> list[dict]:
    res = get_supabase().table("thumbnail_options").select("*").eq("story_id", story_id).execute()
    return res.data


def get_thumbnail_option(option_id: str, story_id: str) -> Optional[dict]:
    res = (
        get_supabase()
        .table("thumbnail_options")
        .select("*")
        .eq("id", option_id)
        .eq("story_id", story_id)
        .single()
        .execute()
    )
    return res.data if res.data else None
