"""Testes unitarios para api.db.repositories.options_repo."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Title Options
# ---------------------------------------------------------------------------


class TestCreateTitleOptions:
    def test_returns_created_titles(self, mock_supabase):
        titles = [
            {"id": "t-1", "story_id": "story-1", "title_text": "Title A"},
            {"id": "t-2", "story_id": "story-1", "title_text": "Title B"},
            {"id": "t-3", "story_id": "story-1", "title_text": "Title C"},
        ]
        mock_supabase.set_response("title_options", titles)
        from api.db.repositories import options_repo

        result = options_repo.create_title_options([
            {"story_id": "story-1", "title_text": "Title A"},
            {"story_id": "story-1", "title_text": "Title B"},
            {"story_id": "story-1", "title_text": "Title C"},
        ])
        assert len(result) == 3
        assert result[0]["title_text"] == "Title A"
        assert result[2]["title_text"] == "Title C"

    def test_returns_empty_list_when_no_titles(self, mock_supabase):
        mock_supabase.set_response("title_options", [])
        from api.db.repositories import options_repo

        result = options_repo.create_title_options([])
        assert result == []


class TestGetTitleOptions:
    def test_returns_all_title_options(self, mock_supabase):
        titles = [
            {"id": "t-1", "story_id": "story-1", "title_text": "Title A"},
            {"id": "t-2", "story_id": "story-1", "title_text": "Title B"},
        ]
        mock_supabase.set_response("title_options", titles)
        from api.db.repositories import options_repo

        result = options_repo.get_title_options("story-1")
        assert len(result) == 2

    def test_returns_empty_list_when_none_exist(self, mock_supabase):
        mock_supabase.set_response("title_options", [])
        from api.db.repositories import options_repo

        result = options_repo.get_title_options("no-story")
        assert result == []


class TestGetTitleOption:
    def test_returns_single_title_option(self, mock_supabase):
        title_data = {"id": "t-1", "story_id": "story-1", "title_text": "Title A"}
        mock_supabase.set_response("title_options", title_data)
        from api.db.repositories import options_repo

        result = options_repo.get_title_option("t-1", "story-1")
        assert result is not None
        assert result["id"] == "t-1"
        assert result["title_text"] == "Title A"

    def test_returns_none_when_not_found(self, mock_supabase):
        mock_supabase.set_response("title_options", None)
        from api.db.repositories import options_repo

        result = options_repo.get_title_option("nonexistent", "story-1")
        assert result is None

    def test_returns_none_for_empty_data(self, mock_supabase):
        mock_supabase.set_response("title_options", [])
        from api.db.repositories import options_repo

        result = options_repo.get_title_option("nonexistent", "story-1")
        assert result is None


# ---------------------------------------------------------------------------
# Thumbnail Options
# ---------------------------------------------------------------------------


class TestCreateThumbnailOption:
    def test_returns_created_thumbnail(self, mock_supabase):
        thumb_data = {
            "id": "th-1",
            "story_id": "story-1",
            "image_url": "https://storage.example.com/thumb1.jpg",
            "prompt": "A dramatic scene of Rome burning",
        }
        mock_supabase.set_response("thumbnail_options", [thumb_data])
        from api.db.repositories import options_repo

        result = options_repo.create_thumbnail_option({
            "story_id": "story-1",
            "image_url": "https://storage.example.com/thumb1.jpg",
            "prompt": "A dramatic scene of Rome burning",
        })
        assert result["id"] == "th-1"
        assert result["image_url"] == "https://storage.example.com/thumb1.jpg"


class TestGetThumbnailOptions:
    def test_returns_all_thumbnail_options(self, mock_supabase):
        thumbs = [
            {"id": "th-1", "story_id": "story-1", "image_url": "https://example.com/1.jpg"},
            {"id": "th-2", "story_id": "story-1", "image_url": "https://example.com/2.jpg"},
            {"id": "th-3", "story_id": "story-1", "image_url": "https://example.com/3.jpg"},
        ]
        mock_supabase.set_response("thumbnail_options", thumbs)
        from api.db.repositories import options_repo

        result = options_repo.get_thumbnail_options("story-1")
        assert len(result) == 3

    def test_returns_empty_list_when_none_exist(self, mock_supabase):
        mock_supabase.set_response("thumbnail_options", [])
        from api.db.repositories import options_repo

        result = options_repo.get_thumbnail_options("no-story")
        assert result == []


class TestGetThumbnailOption:
    def test_returns_single_thumbnail_option(self, mock_supabase):
        thumb_data = {
            "id": "th-1",
            "story_id": "story-1",
            "image_url": "https://example.com/1.jpg",
            "prompt": "Epic scene",
        }
        mock_supabase.set_response("thumbnail_options", thumb_data)
        from api.db.repositories import options_repo

        result = options_repo.get_thumbnail_option("th-1", "story-1")
        assert result is not None
        assert result["id"] == "th-1"
        assert result["image_url"] == "https://example.com/1.jpg"

    def test_returns_none_when_not_found(self, mock_supabase):
        mock_supabase.set_response("thumbnail_options", None)
        from api.db.repositories import options_repo

        result = options_repo.get_thumbnail_option("nonexistent", "story-1")
        assert result is None

    def test_returns_none_for_empty_data(self, mock_supabase):
        mock_supabase.set_response("thumbnail_options", [])
        from api.db.repositories import options_repo

        result = options_repo.get_thumbnail_option("nonexistent", "story-1")
        assert result is None
