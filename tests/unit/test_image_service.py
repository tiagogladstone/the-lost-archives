"""Testes unitarios para api.services.image."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

FAKE_STORY = {
    "id": "story-1",
    "topic": "Ancient Rome",
    "style": "cinematic",
    "aspect_ratio": "16:9",
}

FAKE_SCENE_1 = {
    "id": "scene-1",
    "story_id": "story-1",
    "scene_order": 1,
    "text_content": "Rome was a mighty empire.",
    "image_url": None,
}

FAKE_SCENE_2 = {
    "id": "scene-2",
    "story_id": "story-1",
    "scene_order": 2,
    "text_content": "Gladiators fought in the Colosseum.",
    "image_url": None,
}

FAKE_SCENE_WITH_IMAGE = {
    "id": "scene-3",
    "story_id": "story-1",
    "scene_order": 1,
    "text_content": "Already has an image.",
    "image_url": "https://storage.example.com/images/scene-3.png",
}


# ── Tests: generate_images_for_story ──────────────────────────────────────────


class TestGenerateImagesForStory:
    @pytest.mark.asyncio
    @patch("api.services.image.generate_image_for_scene", new_callable=AsyncMock)
    @patch("api.services.image.scene_repo")
    @patch("api.services.image.story_repo")
    async def test_generate_images_for_story_success(
        self, mock_story_repo, mock_scene_repo, mock_gen_scene
    ):
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY
        mock_scene_repo.get_scenes_by_story.return_value = [FAKE_SCENE_1, FAKE_SCENE_2]
        mock_gen_scene.return_value = "https://storage.example.com/images/scene.png"

        from api.services.image import generate_images_for_story

        # Act
        result = await generate_images_for_story("story-1")

        # Assert
        assert result == 2
        mock_story_repo.get_story.assert_called_once_with("story-1")
        mock_scene_repo.get_scenes_by_story.assert_called_once_with("story-1")
        assert mock_gen_scene.call_count == 2
        mock_gen_scene.assert_any_call("scene-1", FAKE_STORY)
        mock_gen_scene.assert_any_call("scene-2", FAKE_STORY)

    @pytest.mark.asyncio
    @patch("api.services.image.generate_image_for_scene", new_callable=AsyncMock)
    @patch("api.services.image.scene_repo")
    @patch("api.services.image.story_repo")
    async def test_generate_images_skips_existing(
        self, mock_story_repo, mock_scene_repo, mock_gen_scene
    ):
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY
        mock_scene_repo.get_scenes_by_story.return_value = [FAKE_SCENE_WITH_IMAGE]

        from api.services.image import generate_images_for_story

        # Act
        result = await generate_images_for_story("story-1")

        # Assert
        assert result == 0
        mock_gen_scene.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.image.scene_repo")
    @patch("api.services.image.story_repo")
    async def test_story_not_found(self, mock_story_repo, mock_scene_repo):
        # Arrange
        mock_story_repo.get_story.return_value = None

        from api.services.image import generate_images_for_story

        # Act & Assert
        with pytest.raises(ValueError, match="Story story-99 not found"):
            await generate_images_for_story("story-99")

        mock_scene_repo.get_scenes_by_story.assert_not_called()


# ── Tests: generate_image_for_scene ───────────────────────────────────────────


class TestGenerateImageForScene:
    @pytest.mark.asyncio
    @patch("api.services.image.upload_file")
    @patch("api.services.image._imagen_client")
    @patch("api.services.image.genai")
    @patch("api.services.image.scene_repo")
    async def test_generate_image_for_scene_success(
        self, mock_scene_repo, mock_genai, mock_imagen, mock_upload
    ):
        # Arrange
        mock_scene_repo.get_scene.return_value = FAKE_SCENE_1

        # Mock Gemini prompt generation
        mock_prompt_response = MagicMock()
        mock_prompt_response.text = "A cinematic shot of ancient Rome at sunset"
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_prompt_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Mock Imagen image generation
        mock_image = MagicMock()
        mock_image.image.save = MagicMock()  # save to temp file
        mock_image_response = MagicMock()
        mock_image_response.generated_images = [mock_image]
        mock_imagen.models.generate_images.return_value = mock_image_response

        # Mock upload
        mock_upload.return_value = "https://storage.example.com/images/story-1/scene-1.png"

        # Mock update_scene
        mock_scene_repo.update_scene.return_value = FAKE_SCENE_1

        from api.services.image import generate_image_for_scene

        # Act — use patch for open & os.unlink to avoid real file I/O
        with patch("builtins.open", MagicMock()), \
             patch("api.services.image.os.unlink"):
            result = await generate_image_for_scene("scene-1", FAKE_STORY)

        # Assert
        assert result == "https://storage.example.com/images/story-1/scene-1.png"
        mock_scene_repo.get_scene.assert_called_once_with("scene-1")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")
        mock_imagen.models.generate_images.assert_called_once()
        mock_scene_repo.update_scene.assert_called_once()

        update_args = mock_scene_repo.update_scene.call_args
        assert update_args[0][0] == "scene-1"
        assert "image_url" in update_args[0][1]
        assert "image_prompt" in update_args[0][1]
