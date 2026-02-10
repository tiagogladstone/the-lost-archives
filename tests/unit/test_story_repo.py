"""Testes unitarios para api.db.repositories.story_repo."""

from __future__ import annotations


class TestCreateStory:
    def test_returns_created_story(self, mock_supabase):
        mock_supabase.set_response(
            "stories",
            [{"id": "uuid-1", "topic": "Rome", "status": "draft", "style": "cinematic", "aspect_ratio": "16:9"}],
        )
        from api.db.repositories import story_repo

        result = story_repo.create_story({"topic": "Rome", "status": "draft"})
        assert result["id"] == "uuid-1"
        assert result["topic"] == "Rome"
        assert result["status"] == "draft"


class TestGetStory:
    def test_returns_story_when_found(self, mock_supabase):
        story_data = {
            "id": "uuid-1",
            "topic": "Rome",
            "status": "scripting",
            "style": "cinematic",
            "aspect_ratio": "16:9",
        }
        mock_supabase.set_response("stories", story_data)
        from api.db.repositories import story_repo

        result = story_repo.get_story("uuid-1")
        assert result is not None
        assert result["id"] == "uuid-1"
        assert result["topic"] == "Rome"

    def test_returns_none_when_not_found(self, mock_supabase):
        mock_supabase.set_response("stories", None)
        from api.db.repositories import story_repo

        result = story_repo.get_story("nonexistent")
        assert result is None

    def test_returns_none_for_empty_list(self, mock_supabase):
        mock_supabase.set_response("stories", [])
        from api.db.repositories import story_repo

        # empty list is falsy, should return None
        result = story_repo.get_story("nonexistent")
        assert result is None


class TestListStories:
    def test_returns_list_of_stories(self, mock_supabase):
        stories = [
            {"id": "uuid-1", "topic": "Rome", "status": "draft"},
            {"id": "uuid-2", "topic": "Egypt", "status": "scripting"},
        ]
        mock_supabase.set_response("stories", stories)
        from api.db.repositories import story_repo

        result = story_repo.list_stories()
        assert len(result) == 2
        assert result[0]["topic"] == "Rome"
        assert result[1]["topic"] == "Egypt"

    def test_returns_empty_list_when_no_stories(self, mock_supabase):
        mock_supabase.set_response("stories", [])
        from api.db.repositories import story_repo

        result = story_repo.list_stories()
        assert result == []

    def test_with_status_filter(self, mock_supabase):
        mock_supabase.set_response(
            "stories",
            [{"id": "uuid-1", "topic": "Rome", "status": "draft"}],
        )
        from api.db.repositories import story_repo

        result = story_repo.list_stories(status="draft")
        assert len(result) == 1
        assert result[0]["status"] == "draft"

    def test_with_limit_and_offset(self, mock_supabase):
        mock_supabase.set_response("stories", [{"id": "uuid-3", "topic": "Greece", "status": "draft"}])
        from api.db.repositories import story_repo

        result = story_repo.list_stories(limit=1, offset=2)
        assert len(result) == 1


class TestUpdateStory:
    def test_returns_updated_story(self, mock_supabase):
        mock_supabase.set_response(
            "stories",
            [{"id": "uuid-1", "topic": "Rome updated", "status": "scripting"}],
        )
        from api.db.repositories import story_repo

        result = story_repo.update_story("uuid-1", {"topic": "Rome updated"})
        assert result["topic"] == "Rome updated"

    def test_returns_empty_dict_when_not_found(self, mock_supabase):
        mock_supabase.set_response("stories", [])
        from api.db.repositories import story_repo

        result = story_repo.update_story("nonexistent", {"topic": "test"})
        assert result == {}


class TestDeleteStory:
    def test_delete_completes_without_error(self, mock_supabase):
        mock_supabase.set_response("stories", [])
        from api.db.repositories import story_repo

        # delete_story returns None; just verify it doesn't raise
        story_repo.delete_story("uuid-1")


class TestUpdateStatus:
    def test_updates_status(self, mock_supabase):
        mock_supabase.set_response("stories", [])
        from api.db.repositories import story_repo

        # update_status returns None; just verify it doesn't raise
        story_repo.update_status("uuid-1", "scripting")

    def test_updates_status_with_error_message(self, mock_supabase):
        mock_supabase.set_response("stories", [])
        from api.db.repositories import story_repo

        story_repo.update_status("uuid-1", "failed", error_message="Pipeline crashed")
