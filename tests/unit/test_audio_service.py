"""Testes unitarios para api.services.audio."""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ──────────────────────────────────────────────────────────────────

FAKE_STORY = {
    "id": "story-1",
    "topic": "Ancient Rome",
    "languages": ["en-US"],
}

FAKE_SCENE_1 = {
    "id": "scene-1",
    "story_id": "story-1",
    "scene_order": 1,
    "text_content": "Rome was a mighty empire that lasted centuries.",
    "audio_url": None,
}

FAKE_SCENE_2 = {
    "id": "scene-2",
    "story_id": "story-1",
    "scene_order": 2,
    "text_content": "Gladiators were brave fighters.",
    "audio_url": None,
}

FAKE_VOICES = {
    "en-US": {
        "voice_name": "en-US-Wavenet-D",
        "language_code": "en-US",
    },
}


# ── Tests: _chunk_text ────────────────────────────────────────────────────────


class TestChunkText:
    def test_chunk_text_short(self):
        """Texto menor que o limite retorna lista com um elemento."""
        from api.services.audio import _chunk_text

        result = _chunk_text("Short text under limit.", limit=5000)

        assert result == ["Short text under limit."]

    def test_chunk_text_long(self):
        """Texto maior que o limite eh dividido em chunks, cada um abaixo do limite."""
        from api.services.audio import _chunk_text

        # Build a long text with distinct sentences
        sentences = [f"Sentence number {i} about history." for i in range(200)]
        long_text = " ".join(sentences)
        limit = 500

        result = _chunk_text(long_text, limit=limit)

        assert len(result) > 1
        for chunk in result:
            assert len(chunk) <= limit
        # All original content should be present (joined chunks ~ original text)
        rejoined = " ".join(result)
        for i in range(200):
            assert f"Sentence number {i}" in rejoined


# ── Tests: _synthesize_chunk ──────────────────────────────────────────────────


class TestSynthesizeChunk:
    @patch("api.services.audio.requests")
    def test_synthesize_chunk_success(self, mock_requests):
        """Chamada TTS com payload correto retorna bytes decodificados."""
        # Arrange
        fake_audio = b"fake-audio-bytes"
        fake_b64 = base64.b64encode(fake_audio).decode()

        mock_response = MagicMock()
        mock_response.json.return_value = {"audioContent": fake_b64}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        from api.services.audio import _synthesize_chunk

        # Act
        result = _synthesize_chunk("Hello world.", "en-US-Wavenet-D", "en-US")

        # Assert
        assert result == fake_audio
        mock_requests.post.assert_called_once()
        call_kwargs = mock_requests.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        assert payload["input"]["text"] == "Hello world."
        assert payload["voice"]["name"] == "en-US-Wavenet-D"
        assert payload["voice"]["languageCode"] == "en-US"
        assert payload["audioConfig"]["audioEncoding"] == "MP3"


# ── Tests: generate_audio_for_story ───────────────────────────────────────────


class TestGenerateAudioForStory:
    @pytest.mark.asyncio
    @patch("api.services.audio._get_audio_duration", return_value=5.0)
    @patch("api.services.audio.upload_file", return_value="https://storage.example.com/audio/scene.mp3")
    @patch("api.services.audio.requests")
    @patch("api.services.audio.scene_repo")
    @patch("api.services.audio.story_repo")
    async def test_generate_audio_for_story_success(
        self,
        mock_story_repo,
        mock_scene_repo,
        mock_requests,
        mock_upload,
        mock_duration,
    ):
        """Gera audio para todas as cenas sem audio_url."""
        # Arrange
        mock_story_repo.get_story.return_value = FAKE_STORY
        mock_scene_repo.get_scenes_by_story.return_value = [FAKE_SCENE_1, FAKE_SCENE_2]
        mock_scene_repo.get_scene.side_effect = [FAKE_SCENE_1, FAKE_SCENE_2]
        mock_scene_repo.update_scene.return_value = {}

        fake_audio = b"fake-audio-bytes"
        fake_b64 = base64.b64encode(fake_audio).decode()
        mock_response = MagicMock()
        mock_response.json.return_value = {"audioContent": fake_b64}
        mock_response.raise_for_status = MagicMock()
        mock_requests.post.return_value = mock_response

        # Patch VOICES in the audio module
        with patch("api.services.audio.VOICES", FAKE_VOICES):
            from api.services.audio import generate_audio_for_story

            # Act
            result = await generate_audio_for_story("story-1")

        # Assert
        assert result == 2
        mock_story_repo.get_story.assert_called_once_with("story-1")
        mock_scene_repo.get_scenes_by_story.assert_called_once_with("story-1")
        assert mock_scene_repo.update_scene.call_count == 2

    @pytest.mark.asyncio
    @patch("api.services.audio.scene_repo")
    @patch("api.services.audio.story_repo")
    async def test_story_not_found(self, mock_story_repo, mock_scene_repo):
        """ValueError quando story nao existe."""
        # Arrange
        mock_story_repo.get_story.return_value = None

        from api.services.audio import generate_audio_for_story

        # Act & Assert
        with pytest.raises(ValueError, match="Story story-99 not found"):
            await generate_audio_for_story("story-99")

        mock_scene_repo.get_scenes_by_story.assert_not_called()
