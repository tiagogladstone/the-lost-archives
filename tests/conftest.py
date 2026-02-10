"""
Fixtures globais para testes do The Lost Archives.

Ordem de inicialização:
1. Env vars são setadas ANTES de qualquer import de `api.*`
2. YAML loaders são mockados para não depender dos arquivos config/
3. Supabase client é mockado para interceptar toda cadeia de query builder
4. FastAPI TestClient é criado com httpx
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# 1. Env vars — precisam existir ANTES de importar api.config
# ---------------------------------------------------------------------------
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "fake-supabase-key")
os.environ.setdefault("GOOGLE_API_KEY", "fake-google-key")
os.environ.setdefault("API_KEY", "dev-key-change-me")


# ---------------------------------------------------------------------------
# 2. Mock dos YAMLs — api.config carrega no import time
# ---------------------------------------------------------------------------
_FAKE_SETTINGS = {
    "gemini_model": "gemini-2.0-flash",
    "default_language": "en",
    "video_resolution": "1920x1080",
    "music_volume": 0.15,
}
_FAKE_VOICES = {"en": "en-US-Wavenet-D"}
_FAKE_PROMPTS = {"script": "fake prompt"}


def _fake_load_yaml(name: str) -> dict:
    mapping = {
        "settings.yaml": _FAKE_SETTINGS,
        "voices.yaml": _FAKE_VOICES,
        "prompts.yaml": _FAKE_PROMPTS,
    }
    return mapping.get(name, {})


# Patch _load_yaml antes que api.config seja importado pela primeira vez
patch("api.config._load_yaml", side_effect=_fake_load_yaml).start()

# Importa módulos explicitamente para que o patch funcione no Python 3.9
# (sem isso, os sub-módulos não estão registrados e o mock falha)
import api.db.client  # noqa: E402, F401
import api.db.repositories.story_repo  # noqa: E402, F401
import api.db.repositories.scene_repo  # noqa: E402, F401
import api.db.repositories.options_repo  # noqa: E402, F401


# ---------------------------------------------------------------------------
# 3. Supabase mock — query builder fluente
# ---------------------------------------------------------------------------
class SupabaseQueryBuilder:
    """
    Mock que replica a API fluente do Supabase:
        supabase.table("X").select("*").eq("col", val).single().execute()

    Cada chamada encadeada retorna `self`, exceto `.execute()` que retorna
    um SimpleNamespace com `.data`.

    Uso nos testes:
        mock_supabase.set_response("stories", [{"id": "abc", ...}])
        # A próxima chamada a .table("stories")...execute() retornará esses dados
    """

    def __init__(self) -> None:
        # table_name -> data que .execute() retorna
        self._responses: dict[str, Any] = {}
        self._current_table: str | None = None

    # -- Configuração dos dados de resposta ----------------------------------

    def set_response(self, table: str, data: Any) -> None:
        """Define o `.data` que execute() retornará para uma tabela."""
        self._responses[table] = data

    def reset(self) -> None:
        """Limpa todas as respostas configuradas."""
        self._responses.clear()
        self._current_table = None

    # -- API fluente (mesma interface do supabase-py) ------------------------

    def table(self, name: str) -> "SupabaseQueryBuilder":
        self._current_table = name
        return self

    def select(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def insert(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def update(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def delete(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def eq(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def neq(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def gt(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def lt(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def gte(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def lte(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def like(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def ilike(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def is_(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def in_(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def order(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def limit(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def offset(self, *args: Any, **kwargs: Any) -> "SupabaseQueryBuilder":
        return self

    def single(self) -> "SupabaseQueryBuilder":
        return self

    def execute(self) -> SimpleNamespace:
        data = self._responses.get(self._current_table, [])
        return SimpleNamespace(data=data)


@pytest.fixture()
def mock_supabase():
    """
    Fixture que mocka `get_supabase` em todos os locais onde é importado,
    retornando um SupabaseQueryBuilder configurável.

    Uso:
        def test_algo(mock_supabase, client, api_key_header):
            mock_supabase.set_response("stories", [{"id": "abc"}])
            response = client.get("/stories/abc", headers=api_key_header)
            ...
    """
    builder = SupabaseQueryBuilder()
    with patch("api.db.client.get_supabase", return_value=builder), \
         patch("api.db.repositories.story_repo.get_supabase", return_value=builder), \
         patch("api.db.repositories.scene_repo.get_supabase", return_value=builder), \
         patch("api.db.repositories.options_repo.get_supabase", return_value=builder):
        import api.db.client as client_mod
        original = client_mod._client
        client_mod._client = None
        yield builder
        client_mod._client = original


# ---------------------------------------------------------------------------
# 4. FastAPI TestClient
# ---------------------------------------------------------------------------
@pytest.fixture()
def client():
    """
    TestClient síncrono usando httpx (via starlette).

    Importa `api.main.app` — que por sua vez importa api.config
    (já com env vars e YAML mockados).
    """
    from starlette.testclient import TestClient

    from api.main import app

    with TestClient(app, raise_server_exceptions=False) as tc:
        yield tc


# ---------------------------------------------------------------------------
# 5. Header de autenticação
# ---------------------------------------------------------------------------
@pytest.fixture()
def api_key_header() -> dict[str, str]:
    """Header com a API key padrão de desenvolvimento."""
    return {"X-API-Key": "dev-key-change-me"}
