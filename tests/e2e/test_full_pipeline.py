"""Testes E2E do pipeline completo com todos os serviços externos mockados."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Dados de teste
# ---------------------------------------------------------------------------
STORY_ID = "story-test-001"

FAKE_STORY = {
    "id": STORY_ID,
    "topic": "The Fall of Rome",
    "status": "draft",
    "style": "cinematic",
    "aspect_ratio": "16:9",
    "languages": ["en-US", "pt-BR"],
}

FAKE_SCENES = [
    {
        "id": "scene-001",
        "story_id": STORY_ID,
        "scene_order": 1,
        "text_content": "Rome was not built in a day.",
        "image_url": None,
        "audio_url": None,
        "duration_seconds": 10.0,
    },
    {
        "id": "scene-002",
        "story_id": STORY_ID,
        "scene_order": 2,
        "text_content": "But it fell in one.",
        "image_url": None,
        "audio_url": None,
        "duration_seconds": 8.0,
    },
]

# Caminho base para patches no módulo pipeline
_P = "api.services.pipeline"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _build_patches() -> dict[str, AsyncMock | MagicMock]:
    """Cria todos os patches necessários para o pipeline e retorna dict de mocks."""
    return {
        # Repos (sync)
        "story_repo.get_story": MagicMock(return_value=FAKE_STORY),
        "story_repo.update_status": MagicMock(),
        "story_repo.update_story": MagicMock(),
        "scene_repo.get_scenes_by_story": MagicMock(return_value=FAKE_SCENES),
        # Services (async)
        "script_service.generate_script": AsyncMock(return_value=len(FAKE_SCENES)),
        "image_service.generate_image_for_scene": AsyncMock(return_value="https://storage/image.png"),
        "audio_service.generate_audio_for_scene": AsyncMock(return_value="https://storage/audio.mp3"),
        "translation_service.translate_scene": AsyncMock(return_value={"pt-BR": "Traduzido"}),
        "render_service.render_video": AsyncMock(return_value="https://storage/video.mp4"),
        "thumbnail_service.generate_thumbnails": AsyncMock(return_value=3),
        "metadata_service.generate_metadata": AsyncMock(return_value=3),
    }


# ---------------------------------------------------------------------------
# test_full_pipeline_success
# ---------------------------------------------------------------------------
class TestFullPipelineSuccess:
    @pytest.mark.asyncio
    async def test_status_progression_and_service_calls(self):
        """Pipeline completo deve seguir a progressão de status correta
        e chamar todos os serviços."""
        mocks = _build_patches()

        # Aplica todos os patches de uma vez
        patchers = {key: patch(f"{_P}.{key}", mocks[key]) for key in mocks}
        for p in patchers.values():
            p.start()

        try:
            from api.services.pipeline import run_pipeline

            await run_pipeline(STORY_ID)

            update_status = mocks["story_repo.update_status"]

            # Progressão de status: scripting → producing → rendering → post_production → ready_for_review
            expected_calls = [
                call(STORY_ID, "scripting"),
                call(STORY_ID, "producing"),
                call(STORY_ID, "rendering"),
                call(STORY_ID, "post_production"),
                call(STORY_ID, "ready_for_review"),
            ]
            update_status.assert_has_calls(expected_calls, any_order=False)
            assert update_status.call_count == 5

            # get_story chamado 2x (início + reload pós-script)
            assert mocks["story_repo.get_story"].call_count == 2

            # Script
            mocks["script_service.generate_script"].assert_awaited_once_with(STORY_ID)

            # Scenes recarregadas
            mocks["scene_repo.get_scenes_by_story"].assert_called_once_with(STORY_ID)

            # Image — 1 chamada por cena (2 cenas)
            assert mocks["image_service.generate_image_for_scene"].await_count == 2
            mocks["image_service.generate_image_for_scene"].assert_any_await(
                "scene-001", FAKE_STORY
            )
            mocks["image_service.generate_image_for_scene"].assert_any_await(
                "scene-002", FAKE_STORY
            )

            # Audio — 1 chamada por cena (2 cenas)
            assert mocks["audio_service.generate_audio_for_scene"].await_count == 2
            mocks["audio_service.generate_audio_for_scene"].assert_any_await(
                "scene-001", FAKE_STORY
            )
            mocks["audio_service.generate_audio_for_scene"].assert_any_await(
                "scene-002", FAKE_STORY
            )

            # Translation — 1 chamada por cena (2 cenas, languages > 1)
            assert mocks["translation_service.translate_scene"].await_count == 2
            mocks["translation_service.translate_scene"].assert_any_await(
                "scene-001", "en-US", ["pt-BR"]
            )
            mocks["translation_service.translate_scene"].assert_any_await(
                "scene-002", "en-US", ["pt-BR"]
            )

            # Render
            mocks["render_service.render_video"].assert_awaited_once_with(STORY_ID)

            # Thumbnails + Metadata
            mocks["thumbnail_service.generate_thumbnails"].assert_awaited_once_with(STORY_ID)
            mocks["metadata_service.generate_metadata"].assert_awaited_once_with(STORY_ID)

        finally:
            for p in patchers.values():
                p.stop()

    @pytest.mark.asyncio
    async def test_single_language_skips_translation(self):
        """Se a story tem apenas 1 idioma, a tradução NÃO deve ser chamada."""
        story_single_lang = {**FAKE_STORY, "languages": ["en-US"]}
        mocks = _build_patches()
        mocks["story_repo.get_story"] = MagicMock(return_value=story_single_lang)

        patchers = {key: patch(f"{_P}.{key}", mocks[key]) for key in mocks}
        for p in patchers.values():
            p.start()

        try:
            from api.services.pipeline import run_pipeline

            await run_pipeline(STORY_ID)

            # Translation NÃO deve ser chamada
            mocks["translation_service.translate_scene"].assert_not_awaited()

            # Mas o restante sim
            mocks["script_service.generate_script"].assert_awaited_once()
            mocks["image_service.generate_image_for_scene"].assert_awaited()
            mocks["audio_service.generate_audio_for_scene"].assert_awaited()
            mocks["render_service.render_video"].assert_awaited_once()
            mocks["thumbnail_service.generate_thumbnails"].assert_awaited_once()
            mocks["metadata_service.generate_metadata"].assert_awaited_once()

        finally:
            for p in patchers.values():
                p.stop()


# ---------------------------------------------------------------------------
# test_full_pipeline_failure
# ---------------------------------------------------------------------------
class TestFullPipelineFailure:
    @pytest.mark.asyncio
    async def test_script_error_marks_failed(self):
        """Se generate_script falhar, o status deve ir para 'failed' com error_message."""
        mocks = _build_patches()
        mocks["script_service.generate_script"] = AsyncMock(
            side_effect=RuntimeError("API failed")
        )

        patchers = {key: patch(f"{_P}.{key}", mocks[key]) for key in mocks}
        for p in patchers.values():
            p.start()

        try:
            from api.services.pipeline import run_pipeline

            await run_pipeline(STORY_ID)

            update_status = mocks["story_repo.update_status"]

            # Deve ter chamado "scripting" e depois "failed"
            calls = update_status.call_args_list
            assert calls[0] == call(STORY_ID, "scripting")
            assert calls[-1] == call(STORY_ID, "failed", error_message="API failed")

            # Services subsequentes NÃO devem ter sido chamados
            mocks["image_service.generate_image_for_scene"].assert_not_awaited()
            mocks["audio_service.generate_audio_for_scene"].assert_not_awaited()
            mocks["render_service.render_video"].assert_not_awaited()
            mocks["thumbnail_service.generate_thumbnails"].assert_not_awaited()
            mocks["metadata_service.generate_metadata"].assert_not_awaited()

        finally:
            for p in patchers.values():
                p.stop()

    @pytest.mark.asyncio
    async def test_render_error_marks_failed(self):
        """Se render_video falhar, o status deve ir para 'failed' com error_message."""
        mocks = _build_patches()
        mocks["render_service.render_video"] = AsyncMock(
            side_effect=RuntimeError("FFmpeg crashed")
        )

        patchers = {key: patch(f"{_P}.{key}", mocks[key]) for key in mocks}
        for p in patchers.values():
            p.start()

        try:
            from api.services.pipeline import run_pipeline

            await run_pipeline(STORY_ID)

            update_status = mocks["story_repo.update_status"]
            calls = update_status.call_args_list

            # Deve ter passado por scripting, producing, rendering, e depois failed
            assert calls[0] == call(STORY_ID, "scripting")
            assert calls[1] == call(STORY_ID, "producing")
            assert calls[2] == call(STORY_ID, "rendering")
            assert calls[-1] == call(STORY_ID, "failed", error_message="FFmpeg crashed")

            # Post-production NÃO deve ter sido chamado
            mocks["thumbnail_service.generate_thumbnails"].assert_not_awaited()
            mocks["metadata_service.generate_metadata"].assert_not_awaited()

        finally:
            for p in patchers.values():
                p.stop()

    @pytest.mark.asyncio
    async def test_story_not_found_marks_failed(self):
        """Se get_story retornar None, o pipeline deve falhar com ValueError."""
        mocks = _build_patches()
        mocks["story_repo.get_story"] = MagicMock(return_value=None)

        patchers = {key: patch(f"{_P}.{key}", mocks[key]) for key in mocks}
        for p in patchers.values():
            p.start()

        try:
            from api.services.pipeline import run_pipeline

            await run_pipeline(STORY_ID)

            update_status = mocks["story_repo.update_status"]
            calls = update_status.call_args_list

            # Deve ter ido direto para failed (sem scripting)
            assert len(calls) == 1
            assert calls[0] == call(
                STORY_ID, "failed", error_message=f"Story {STORY_ID} not found"
            )

        finally:
            for p in patchers.values():
                p.stop()


# ---------------------------------------------------------------------------
# test_publish_success
# ---------------------------------------------------------------------------
class TestPublishSuccess:
    @pytest.mark.asyncio
    async def test_publish_calls_upload_and_updates_status(self):
        """publish() deve atualizar status para 'publishing' → 'published'."""
        mock_update_status = MagicMock()
        mock_upload = AsyncMock(return_value="https://youtube.com/watch?v=xxx")

        with patch(f"{_P}.story_repo.update_status", mock_update_status), \
             patch(f"{_P}.upload_service.upload_to_youtube", mock_upload):
            from api.services.pipeline import publish

            await publish(STORY_ID)

            # Progressão: publishing → published
            expected_calls = [
                call(STORY_ID, "publishing"),
                call(STORY_ID, "published"),
            ]
            mock_update_status.assert_has_calls(expected_calls, any_order=False)
            assert mock_update_status.call_count == 2

            # Upload foi chamado com o story_id
            mock_upload.assert_awaited_once_with(STORY_ID)

    @pytest.mark.asyncio
    async def test_publish_failure_marks_failed(self):
        """Se upload_to_youtube falhar, o status deve ir para 'failed'."""
        mock_update_status = MagicMock()
        mock_upload = AsyncMock(side_effect=RuntimeError("YouTube quota exceeded"))

        with patch(f"{_P}.story_repo.update_status", mock_update_status), \
             patch(f"{_P}.upload_service.upload_to_youtube", mock_upload):
            from api.services.pipeline import publish

            await publish(STORY_ID)

            calls = mock_update_status.call_args_list

            assert calls[0] == call(STORY_ID, "publishing")
            assert calls[-1] == call(
                STORY_ID, "failed", error_message="YouTube quota exceeded"
            )
