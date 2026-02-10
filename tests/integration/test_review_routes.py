"""Testes de integracao para os endpoints de review e publish."""

from __future__ import annotations

from unittest.mock import patch

STORY_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TITLE_OPT_ID = "11111111-1111-1111-1111-111111111111"
THUMB_OPT_ID = "22222222-2222-2222-2222-222222222222"
NOW = "2025-01-01T00:00:00+00:00"


def _make_story(**overrides) -> dict:
    base = {
        "id": STORY_ID,
        "topic": "The Fall of Rome",
        "description": "How Rome fell",
        "target_duration_minutes": 8,
        "languages": ["en-US"],
        "style": "cinematic",
        "aspect_ratio": "16:9",
        "status": "ready_for_review",
        "script_text": None,
        "selected_title": None,
        "selected_thumbnail_url": None,
        "video_url": "https://storage.example.com/video.mp4",
        "youtube_url": None,
        "metadata": {"description": "A story about Rome", "tags": ["rome"]},
        "error_message": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    base.update(overrides)
    return base


def _make_title_options() -> list[dict]:
    return [
        {"id": TITLE_OPT_ID, "story_id": STORY_ID, "title_text": "The Fall of Rome"},
        {"id": "33333333-3333-3333-3333-333333333333", "story_id": STORY_ID, "title_text": "Rome's Last Days"},
        {"id": "44444444-4444-4444-4444-444444444444", "story_id": STORY_ID, "title_text": "When Rome Burned"},
    ]


def _make_thumbnail_options() -> list[dict]:
    return [
        {"id": THUMB_OPT_ID, "story_id": STORY_ID, "image_url": "https://example.com/thumb1.jpg", "prompt": "Rome burning"},
        {"id": "55555555-5555-5555-5555-555555555555", "story_id": STORY_ID, "image_url": "https://example.com/thumb2.jpg", "prompt": "Colosseum"},
    ]


# ---------------------------------------------------------------------------
# GET /stories/{id}/review
# ---------------------------------------------------------------------------


class TestGetReview:
    def test_returns_200_when_ready_for_review(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story())
        mock_supabase.set_response("title_options", _make_title_options())
        mock_supabase.set_response("thumbnail_options", _make_thumbnail_options())

        resp = client.get(f"/stories/{STORY_ID}/review", headers=api_key_header)
        assert resp.status_code == 200

        data = resp.json()
        assert data["story_id"] == STORY_ID
        assert len(data["title_options"]) == 3
        assert len(data["thumbnail_options"]) == 2
        assert data["video_url"] == "https://storage.example.com/video.mp4"

    def test_returns_400_when_not_ready(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story(status="scripting"))

        resp = client.get(f"/stories/{STORY_ID}/review", headers=api_key_header)
        assert resp.status_code == 400
        assert "not ready for review" in resp.json()["detail"].lower()

    def test_returns_400_for_draft_status(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story(status="draft"))

        resp = client.get(f"/stories/{STORY_ID}/review", headers=api_key_header)
        assert resp.status_code == 400

    def test_returns_404_when_story_not_found(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", None)

        resp = client.get(f"/stories/{STORY_ID}/review", headers=api_key_header)
        assert resp.status_code == 404

    def test_returns_metadata(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story())
        mock_supabase.set_response("title_options", [])
        mock_supabase.set_response("thumbnail_options", [])

        resp = client.get(f"/stories/{STORY_ID}/review", headers=api_key_header)
        assert resp.status_code == 200
        assert resp.json()["metadata"]["description"] == "A story about Rome"


# ---------------------------------------------------------------------------
# POST /stories/{id}/review
# ---------------------------------------------------------------------------


class TestSelectReview:
    def test_returns_200_on_valid_selection(self, mock_supabase, client, api_key_header):
        """
        O mock_supabase retorna o mesmo dado para a mesma tabela, mas
        get_title_option (singular, dict) e get_title_options (plural, lista) usam
        a mesma tabela. Usamos patch nos repos para evitar conflito.
        """
        title_opt = {"id": TITLE_OPT_ID, "story_id": STORY_ID, "title_text": "The Fall of Rome"}
        thumb_opt = {"id": THUMB_OPT_ID, "story_id": STORY_ID, "image_url": "https://example.com/thumb1.jpg", "prompt": "Rome burning"}

        mock_supabase.set_response("stories", _make_story())

        with (
            patch("api.db.repositories.options_repo.get_title_option", return_value=title_opt),
            patch("api.db.repositories.options_repo.get_thumbnail_option", return_value=thumb_opt),
            patch("api.db.repositories.options_repo.get_title_options", return_value=_make_title_options()),
            patch("api.db.repositories.options_repo.get_thumbnail_options", return_value=_make_thumbnail_options()),
            patch("api.db.repositories.story_repo.update_story", return_value=_make_story()),
        ):
            resp = client.post(
                f"/stories/{STORY_ID}/review",
                json={
                    "title_option_id": TITLE_OPT_ID,
                    "thumbnail_option_id": THUMB_OPT_ID,
                },
                headers=api_key_header,
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["story_id"] == STORY_ID
        assert len(data["title_options"]) == 3
        assert len(data["thumbnail_options"]) == 2

    def test_returns_404_when_story_not_found(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", None)

        resp = client.post(
            f"/stories/{STORY_ID}/review",
            json={
                "title_option_id": TITLE_OPT_ID,
                "thumbnail_option_id": THUMB_OPT_ID,
            },
            headers=api_key_header,
        )
        assert resp.status_code == 404

    def test_returns_400_when_not_ready_for_review(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story(status="publishing"))

        resp = client.post(
            f"/stories/{STORY_ID}/review",
            json={
                "title_option_id": TITLE_OPT_ID,
                "thumbnail_option_id": THUMB_OPT_ID,
            },
            headers=api_key_header,
        )
        assert resp.status_code == 400

    def test_returns_404_when_title_option_not_found(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story())

        with patch("api.db.repositories.options_repo.get_title_option", return_value=None):
            resp = client.post(
                f"/stories/{STORY_ID}/review",
                json={
                    "title_option_id": TITLE_OPT_ID,
                    "thumbnail_option_id": THUMB_OPT_ID,
                },
                headers=api_key_header,
            )

        assert resp.status_code == 404
        assert "title option" in resp.json()["detail"].lower()

    def test_returns_404_when_thumbnail_option_not_found(self, mock_supabase, client, api_key_header):
        title_opt = {"id": TITLE_OPT_ID, "story_id": STORY_ID, "title_text": "The Fall of Rome"}
        mock_supabase.set_response("stories", _make_story())

        with (
            patch("api.db.repositories.options_repo.get_title_option", return_value=title_opt),
            patch("api.db.repositories.options_repo.get_thumbnail_option", return_value=None),
        ):
            resp = client.post(
                f"/stories/{STORY_ID}/review",
                json={
                    "title_option_id": TITLE_OPT_ID,
                    "thumbnail_option_id": THUMB_OPT_ID,
                },
                headers=api_key_header,
            )

        assert resp.status_code == 404
        assert "thumbnail option" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /stories/{id}/publish
# ---------------------------------------------------------------------------


class TestPublish:
    def test_returns_202_on_success(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response(
            "stories",
            _make_story(
                selected_title="The Fall of Rome",
                selected_thumbnail_url="https://example.com/thumb1.jpg",
            ),
        )

        with patch("api.services.pipeline.publish", return_value=None):
            resp = client.post(f"/stories/{STORY_ID}/publish", headers=api_key_header)

        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "publishing"
        assert "message" in data

    def test_returns_404_when_story_not_found(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", None)

        resp = client.post(f"/stories/{STORY_ID}/publish", headers=api_key_header)
        assert resp.status_code == 404

    def test_returns_400_when_not_ready_for_review(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response("stories", _make_story(status="rendering"))

        resp = client.post(f"/stories/{STORY_ID}/publish", headers=api_key_header)
        assert resp.status_code == 400
        assert "not in publishable state" in resp.json()["detail"].lower()

    def test_returns_400_when_title_not_selected(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response(
            "stories",
            _make_story(selected_title=None, selected_thumbnail_url="https://example.com/thumb.jpg"),
        )

        resp = client.post(f"/stories/{STORY_ID}/publish", headers=api_key_header)
        assert resp.status_code == 400
        assert "must be selected" in resp.json()["detail"].lower()

    def test_returns_400_when_thumbnail_not_selected(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response(
            "stories",
            _make_story(selected_title="My Title", selected_thumbnail_url=None),
        )

        resp = client.post(f"/stories/{STORY_ID}/publish", headers=api_key_header)
        assert resp.status_code == 400
        assert "must be selected" in resp.json()["detail"].lower()

    def test_returns_400_when_both_not_selected(self, mock_supabase, client, api_key_header):
        mock_supabase.set_response(
            "stories",
            _make_story(selected_title=None, selected_thumbnail_url=None),
        )

        resp = client.post(f"/stories/{STORY_ID}/publish", headers=api_key_header)
        assert resp.status_code == 400
