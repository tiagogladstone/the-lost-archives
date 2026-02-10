"""Testes de integracao para os endpoints de /stories."""

from __future__ import annotations

from unittest.mock import patch

# UUIDs fixos para testes
STORY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
NOW = "2025-01-01T00:00:00+00:00"


def _make_story(**overrides) -> dict:
    """Fabrica de story dict com defaults razoaveis."""
    base = {
        "id": STORY_ID,
        "topic": "The Fall of Rome",
        "description": "How Rome fell",
        "target_duration_minutes": 8,
        "languages": ["en-US"],
        "style": "cinematic",
        "aspect_ratio": "16:9",
        "status": "draft",
        "script_text": None,
        "selected_title": None,
        "selected_thumbnail_url": None,
        "video_url": None,
        "youtube_url": None,
        "metadata": {},
        "error_message": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /stories
# ---------------------------------------------------------------------------


class TestCreateStory:
    def test_returns_201_on_success(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", [_make_story()])

        with patch("api.services.pipeline.run_pipeline", return_value=None):
            resp = client.post(
                "/stories",
                json={"topic": "The Fall of Rome"},
                headers=api_key_header,
            )

        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == STORY_ID
        assert data["topic"] == "The Fall of Rome"
        assert data["status"] == "draft"

    def test_returns_201_even_if_pipeline_not_implemented(self, mock_supabase, client, api_key_header):
        """Se pipeline nao existir (ImportError), story ainda e criada."""
        mock_supabase.set_response("stories", [_make_story()])

        with patch("api.routes.stories.story_repo.create_story", return_value=_make_story()):
            resp = client.post(
                "/stories",
                json={"topic": "The Fall of Rome"},
                headers=api_key_header,
            )

        assert resp.status_code == 201

    def test_validates_style_field(self, mock_supabase, client, api_key_header):
        resp = client.post(
            "/stories",
            json={"topic": "Test", "style": "watercolor"},
            headers=api_key_header,
        )
        assert resp.status_code == 422

    def test_validates_aspect_ratio_field(self, mock_supabase, client, api_key_header):
        resp = client.post(
            "/stories",
            json={"topic": "Test", "aspect_ratio": "4:3"},
            headers=api_key_header,
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /stories
# ---------------------------------------------------------------------------


class TestListStories:
    def test_returns_200_with_stories(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", [
            _make_story(id="a1b2c3d4-e5f6-7890-abcd-ef1234567891", topic="Rome"),
            _make_story(id="a1b2c3d4-e5f6-7890-abcd-ef1234567892", topic="Egypt"),
        ])

        resp = client.get("/stories", headers=api_key_header)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_returns_200_empty_list(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", [])

        resp = client.get("/stories", headers=api_key_header)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_supports_status_filter(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", [_make_story(status="scripting")])

        resp = client.get("/stories?status=scripting", headers=api_key_header)
        assert resp.status_code == 200

    def test_supports_pagination(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", [_make_story()])

        resp = client.get("/stories?limit=5&offset=10", headers=api_key_header)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /stories/{id}
# ---------------------------------------------------------------------------


class TestGetStoryDetail:
    def test_returns_200_with_detail(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story())
        mock_supabase.set_response("scenes", [])
        mock_supabase.set_response("title_options", [])
        mock_supabase.set_response("thumbnail_options", [])

        resp = client.get(f"/stories/{STORY_ID}", headers=api_key_header)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == STORY_ID
        assert "scenes" in data
        assert "title_options" in data
        assert "thumbnail_options" in data

    def test_returns_200_with_scenes(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story())
        mock_supabase.set_response("scenes", [
            {
                "id": "b1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "story_id": STORY_ID,
                "scene_order": 1,
                "text_content": "Rome was great",
                "translated_text": {},
                "image_prompt": None,
                "image_url": None,
                "audio_url": None,
                "duration_seconds": None,
            },
        ])
        mock_supabase.set_response("title_options", [])
        mock_supabase.set_response("thumbnail_options", [])

        resp = client.get(f"/stories/{STORY_ID}", headers=api_key_header)
        assert resp.status_code == 200
        assert len(resp.json()["scenes"]) == 1

    def test_returns_404_when_not_found(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", None)

        resp = client.get(f"/stories/{STORY_ID}", headers=api_key_header)
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# DELETE /stories/{id}
# ---------------------------------------------------------------------------


class TestDeleteStory:
    def test_returns_204_on_success(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story())

        with patch("api.services.storage.delete_story_files", return_value=None):
            resp = client.delete(f"/stories/{STORY_ID}", headers=api_key_header)

        assert resp.status_code == 204

    def test_returns_404_when_story_not_found(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", None)

        resp = client.delete(f"/stories/{STORY_ID}", headers=api_key_header)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Autenticacao
# ---------------------------------------------------------------------------


class TestAuthentication:
    def test_missing_api_key_returns_422(self, mock_supabase, client):
        resp = client.get("/stories")
        assert resp.status_code == 422

    def test_wrong_api_key_returns_401(self, mock_supabase, client):
        resp = client.get("/stories", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401
        assert "invalid" in resp.json()["detail"].lower()

    def test_post_without_api_key_returns_422(self, mock_supabase, client):
        resp = client.post("/stories", json={"topic": "Test"})
        assert resp.status_code == 422

    def test_delete_with_wrong_api_key_returns_401(self, mock_supabase, client):
        resp = client.delete(f"/stories/{STORY_ID}", headers={"X-API-Key": "wrong-key"})
        assert resp.status_code == 401
