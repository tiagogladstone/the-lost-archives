"""Testes unitarios para api.services.script."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

FAKE_STORY = {
    "id": "story-1",
    "topic": "Ancient Rome",
    "description": "The rise and fall of Rome",
    "target_duration_minutes": 8,
    "style": "cinematic",
}

FAKE_SCRIPT_TEXT = "Paragraph one about Rome.\n\nParagraph two about gladiators.\n\nParagraph three about the fall."


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestGenerateScript:
    @pytest.mark.asyncio
    @patch("api.services.script.genai")
    @patch("api.services.script.scene_repo")
    @patch("api.services.script.story_repo")
    async def test_generate_script_success(
        self, mock_story_repo, mock_scene_repo, mock_genai
    ):
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY

        mock_response = MagicMock()
        mock_response.text = FAKE_SCRIPT_TEXT
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        mock_story_repo.update_story.return_value = FAKE_STORY
        mock_scene_repo.create_scenes_bulk.return_value = []

        from api.services.script import generate_script

        # Act
        result = await generate_script("story-1")

        # Assert
        assert result == 3

        mock_story_repo.get_story.assert_called_once_with("story-1")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")
        mock_model.generate_content.assert_called_once()

        mock_story_repo.update_story.assert_called_once_with(
            "story-1", {"script_text": FAKE_SCRIPT_TEXT}
        )

        mock_scene_repo.create_scenes_bulk.assert_called_once()
        scenes_data = mock_scene_repo.create_scenes_bulk.call_args[0][0]
        assert len(scenes_data) == 3
        assert scenes_data[0]["story_id"] == "story-1"
        assert scenes_data[0]["scene_order"] == 1
        assert scenes_data[0]["text_content"] == "Paragraph one about Rome."
        assert scenes_data[1]["scene_order"] == 2
        assert scenes_data[2]["scene_order"] == 3

    @pytest.mark.asyncio
    @patch("api.services.script.genai")
    @patch("api.services.script.scene_repo")
    @patch("api.services.script.story_repo")
    async def test_generate_script_story_not_found(
        self, mock_story_repo, mock_scene_repo, mock_genai
    ):
        # Arrange
        mock_story_repo.get_story.return_value = None

        from api.services.script import generate_script

        # Act & Assert
        with pytest.raises(ValueError, match="Story story-99 not found"):
            await generate_script("story-99")

        mock_story_repo.get_story.assert_called_once_with("story-99")
        mock_genai.GenerativeModel.assert_not_called()
        mock_scene_repo.create_scenes_bulk.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.script.genai")
    @patch("api.services.script.scene_repo")
    @patch("api.services.script.story_repo")
    async def test_generate_script_empty_response(
        self, mock_story_repo, mock_scene_repo, mock_genai
    ):
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY

        mock_response = MagicMock()
        mock_response.text = ""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        from api.services.script import generate_script

        # Act & Assert
        with pytest.raises(RuntimeError, match="Gemini returned empty script"):
            await generate_script("story-1")

        mock_story_repo.update_story.assert_not_called()
        mock_scene_repo.create_scenes_bulk.assert_not_called()
