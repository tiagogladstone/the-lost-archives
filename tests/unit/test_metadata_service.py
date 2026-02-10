"""Testes unitarios para api.services.metadata."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

FAKE_STORY = {
    "id": "story-1",
    "topic": "Ancient Rome",
    "script_text": "Rome was a mighty empire. Gladiators fought bravely.",
}

VALID_METADATA = {
    "titles": [
        "The Hidden Truth About Ancient Rome",
        "Why Rome Really Fell: The Untold Story",
        "Secrets of the Roman Empire Revealed",
    ],
    "description": "Discover the shocking truths about Ancient Rome...",
    "tags": "ancient rome,history,roman empire,gladiators,documentary",
}


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestGenerateMetadata:
    @pytest.mark.asyncio
    @patch("api.services.metadata.genai")
    @patch("api.services.metadata.options_repo")
    @patch("api.services.metadata.story_repo")
    async def test_generate_metadata_success(
        self, mock_story_repo, mock_options_repo, mock_genai
    ):
        """Gera metadata com sucesso: 3 titulos, descricao e tags."""
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY

        mock_response = MagicMock()
        mock_response.text = json.dumps(VALID_METADATA)
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.types.GenerationConfig = MagicMock()

        mock_options_repo.create_title_options.return_value = []
        mock_story_repo.update_story.return_value = FAKE_STORY

        from api.services.metadata import generate_metadata

        # Act
        result = await generate_metadata("story-1")

        # Assert
        assert result == 3

        mock_story_repo.get_story.assert_called_once_with("story-1")
        mock_genai.GenerativeModel.assert_called_once_with("gemini-2.0-flash")
        mock_model.generate_content.assert_called_once()

        # Verify title options were created
        mock_options_repo.create_title_options.assert_called_once()
        title_records = mock_options_repo.create_title_options.call_args[0][0]
        assert len(title_records) == 3
        for record in title_records:
            assert record["story_id"] == "story-1"
            assert "title_text" in record
        assert title_records[0]["title_text"] == VALID_METADATA["titles"][0]
        assert title_records[1]["title_text"] == VALID_METADATA["titles"][1]
        assert title_records[2]["title_text"] == VALID_METADATA["titles"][2]

        # Verify story metadata updated
        mock_story_repo.update_story.assert_called_once_with(
            "story-1",
            {
                "metadata": {
                    "description": VALID_METADATA["description"],
                    "tags": VALID_METADATA["tags"],
                }
            },
        )

    @pytest.mark.asyncio
    @patch("api.services.metadata.genai")
    @patch("api.services.metadata.options_repo")
    @patch("api.services.metadata.story_repo")
    async def test_story_not_found(
        self, mock_story_repo, mock_options_repo, mock_genai
    ):
        """ValueError quando story nao existe."""
        # Arrange
        mock_story_repo.get_story.return_value = None

        from api.services.metadata import generate_metadata

        # Act & Assert
        with pytest.raises(ValueError, match="Story story-99 not found"):
            await generate_metadata("story-99")

        mock_genai.GenerativeModel.assert_not_called()
        mock_options_repo.create_title_options.assert_not_called()

    @pytest.mark.asyncio
    @patch("api.services.metadata.genai")
    @patch("api.services.metadata.options_repo")
    @patch("api.services.metadata.story_repo")
    async def test_invalid_metadata_missing_titles(
        self, mock_story_repo, mock_options_repo, mock_genai
    ):
        """ValueError quando Gemini retorna JSON sem o campo 'titles'."""
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY

        invalid_metadata = {
            "description": "Some description",
            "tags": "tag1,tag2",
            # "titles" field is missing
        }
        mock_response = MagicMock()
        mock_response.text = json.dumps(invalid_metadata)
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.types.GenerationConfig = MagicMock()

        from api.services.metadata import generate_metadata

        # Act & Assert
        with pytest.raises(ValueError, match="Metadata missing required fields"):
            await generate_metadata("story-1")

        mock_options_repo.create_title_options.assert_not_called()
        mock_story_repo.update_story.assert_not_called()
