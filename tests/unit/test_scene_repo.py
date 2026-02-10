"""Testes unitarios para api.db.repositories.scene_repo."""

from __future__ import annotations


class TestCreateScene:
    def test_returns_created_scene(self, mock_supabase):
        scene_data = {
            "id": "scene-1",
            "story_id": "story-1",
            "scene_order": 1,
            "text_content": "The Roman Empire...",
        }
        mock_supabase.set_response("scenes", [scene_data])
        from api.db.repositories import scene_repo

        result = scene_repo.create_scene({"story_id": "story-1", "scene_order": 1, "text_content": "The Roman Empire..."})
        assert result["id"] == "scene-1"
        assert result["story_id"] == "story-1"
        assert result["scene_order"] == 1


class TestCreateScenesBulk:
    def test_returns_list_of_created_scenes(self, mock_supabase):
        scenes = [
            {"id": "scene-1", "story_id": "story-1", "scene_order": 1, "text_content": "Scene 1"},
            {"id": "scene-2", "story_id": "story-1", "scene_order": 2, "text_content": "Scene 2"},
        ]
        mock_supabase.set_response("scenes", scenes)
        from api.db.repositories import scene_repo

        result = scene_repo.create_scenes_bulk([
            {"story_id": "story-1", "scene_order": 1, "text_content": "Scene 1"},
            {"story_id": "story-1", "scene_order": 2, "text_content": "Scene 2"},
        ])
        assert len(result) == 2
        assert result[0]["scene_order"] == 1
        assert result[1]["scene_order"] == 2

    def test_returns_empty_list_when_no_scenes(self, mock_supabase):
        mock_supabase.set_response("scenes", [])
        from api.db.repositories import scene_repo

        result = scene_repo.create_scenes_bulk([])
        assert result == []


class TestGetScene:
    def test_returns_scene_when_found(self, mock_supabase):
        scene_data = {
            "id": "scene-1",
            "story_id": "story-1",
            "scene_order": 1,
            "text_content": "Text here",
        }
        mock_supabase.set_response("scenes", scene_data)
        from api.db.repositories import scene_repo

        result = scene_repo.get_scene("scene-1")
        assert result is not None
        assert result["id"] == "scene-1"

    def test_returns_none_when_not_found(self, mock_supabase):
        mock_supabase.set_response("scenes", None)
        from api.db.repositories import scene_repo

        result = scene_repo.get_scene("nonexistent")
        assert result is None

    def test_returns_none_for_empty_list(self, mock_supabase):
        mock_supabase.set_response("scenes", [])
        from api.db.repositories import scene_repo

        result = scene_repo.get_scene("nonexistent")
        assert result is None


class TestGetScenesByStory:
    def test_returns_scenes_ordered(self, mock_supabase):
        scenes = [
            {"id": "scene-1", "story_id": "story-1", "scene_order": 1, "text_content": "First"},
            {"id": "scene-2", "story_id": "story-1", "scene_order": 2, "text_content": "Second"},
        ]
        mock_supabase.set_response("scenes", scenes)
        from api.db.repositories import scene_repo

        result = scene_repo.get_scenes_by_story("story-1")
        assert len(result) == 2
        assert result[0]["scene_order"] == 1
        assert result[1]["scene_order"] == 2

    def test_returns_empty_list_when_no_scenes(self, mock_supabase):
        mock_supabase.set_response("scenes", [])
        from api.db.repositories import scene_repo

        result = scene_repo.get_scenes_by_story("story-no-scenes")
        assert result == []


class TestUpdateScene:
    def test_returns_updated_scene(self, mock_supabase):
        mock_supabase.set_response(
            "scenes",
            [{"id": "scene-1", "story_id": "story-1", "scene_order": 1, "text_content": "Updated text"}],
        )
        from api.db.repositories import scene_repo

        result = scene_repo.update_scene("scene-1", {"text_content": "Updated text"})
        assert result["text_content"] == "Updated text"

    def test_returns_empty_dict_when_not_found(self, mock_supabase):
        mock_supabase.set_response("scenes", [])
        from api.db.repositories import scene_repo

        result = scene_repo.update_scene("nonexistent", {"text_content": "test"})
        assert result == {}
