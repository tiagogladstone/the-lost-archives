# The Lost Archives v2

Canal do YouTube totalmente automatizado que gera vídeos sobre história e curiosidades usando IA.

## Stack

- **Backend:** Python 3.11, FastAPI, Supabase (PostgreSQL + Storage)
- **Frontend:** Next.js (App Router) — Fase 5
- **IA:** Google Gemini 2.0 Flash, Imagen 4, Google Cloud TTS (Wavenet)
- **Mídia:** FFmpeg
- **Upload:** YouTube Data API v3 (OAuth 2.0)
- **Infra:** Docker, Google Cloud Run

## Arquitetura: Monolith-first

Tudo em um FastAPI app. Sem job queue, sem workers, sem polling.
Pipeline orquestrado por código Python com asyncio.
Cada "worker" virou uma service function em `api/services/`.

```
                    ┌─────────────┐
                    │  Dashboard   │  (Fase 5)
                    │  Next.js     │
                    └──────┬──────┘
                           │ HTTP
                    ┌──────▼──────┐
                    │   FastAPI    │
                    │   + Services │
                    └──────┬──────┘
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Supabase     Google APIs    FFmpeg
        (DB+Storage)  (Gemini,TTS,
                       Imagen,YT)
```

## Estrutura de Diretórios

```
├── api/
│   ├── main.py                 # FastAPI app
│   ├── config.py               # Env vars + YAML configs
│   ├── dependencies.py         # Auth (API key)
│   ├── routes/
│   │   ├── stories.py          # CRUD: POST/GET/DELETE /stories
│   │   ├── review.py           # GET/POST review, POST publish
│   │   ├── pipeline.py         # POST /pipeline/{id}/{step} (teste)
│   │   └── health.py           # GET /health
│   ├── models/
│   │   ├── story.py            # Pydantic models (request/response)
│   │   ├── scene.py            # SceneResponse
│   │   ├── review.py           # ReviewResponse, SelectReviewRequest
│   │   └── enums.py            # StoryStatus enum
│   ├── services/
│   │   ├── pipeline.py         # Orquestrador: run_pipeline(), publish()
│   │   ├── script.py           # Gemini 2.0 Flash → roteiro + cenas
│   │   ├── image.py            # Imagen 4 → imagem por cena
│   │   ├── audio.py            # Google Cloud TTS → áudio por cena
│   │   ├── translation.py      # Gemini → traduz cenas
│   │   ├── render.py           # FFmpeg → renderiza vídeo
│   │   ├── thumbnail.py        # Imagen 4 → 3 thumbnails
│   │   ├── metadata.py         # Gemini JSON → 3 títulos + desc + tags
│   │   ├── upload.py           # YouTube Data API v3 → upload
│   │   └── storage.py          # Wrapper Supabase Storage
│   └── db/
│       ├── client.py           # Supabase client singleton
│       └── repositories/
│           ├── story_repo.py   # CRUD stories
│           ├── scene_repo.py   # CRUD scenes
│           └── options_repo.py # CRUD title/thumbnail options
├── config/
│   ├── settings.yaml           # Configurações gerais
│   ├── voices.yaml             # Mapeamento idioma → voz TTS
│   └── prompts.yaml            # Prompts do Gemini
├── database/
│   └── schema.sql              # Schema (4 tabelas, sem jobs)
├── workers/                    # LEGADO — referência v1
├── scripts/                    # LEGADO — referência v1
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Fluxo de Status (stories)

```
draft → scripting → producing → rendering → post_production → ready_for_review → publishing → published
                                                                                              → failed
```

## Database (4 tabelas)

- `stories` — principal, com status, style, aspect_ratio
- `scenes` — FK para stories, com translated_text JSONB
- `title_options` — 3 opções de título geradas
- `thumbnail_options` — 3 opções de thumbnail geradas

Sem tabela `jobs`. Sem stored procedure `claim_next_job`.

## Endpoints da API

### CRUD
- `POST /stories` — Cria story + dispara pipeline em background
- `GET /stories` — Lista (filtro por status)
- `GET /stories/{id}` — Detalhe com scenes
- `DELETE /stories/{id}` — Deleta + limpa storage

### Review & Publish
- `GET /stories/{id}/review` — Dados de revisão
- `POST /stories/{id}/review` — Seleciona título + thumbnail
- `POST /stories/{id}/publish` — Upload YouTube

### Pipeline (teste individual)
- `POST /pipeline/{id}/{step}` — script, images, audio, translate, render, thumbnails, metadata

### Health
- `GET /health`

## Variáveis de Ambiente

```
SUPABASE_URL          # URL do projeto Supabase
SUPABASE_KEY          # Service role key
GOOGLE_API_KEY        # Gemini + Imagen + TTS
YOUTUBE_TOKEN_JSON    # Base64 encoded OAuth2 credentials
API_KEY               # Autenticação da API
PORT                  # Porta (default 8000)
```

## Convenções

- Services são async functions, não classes
- Pipeline orquestrado por `asyncio.gather` (paralelo por cena)
- Storage wrapper centraliza upload/download/URL
- Repositories abstraem queries Supabase
- Config carregado via `api/config.py` (env + YAML)
- Autenticação: header `X-API-Key`

## Comandos

```bash
# API (dev)
uvicorn api.main:app --reload --port 8000

# Swagger UI
open http://localhost:8000/docs

# Docker
docker build -t the-lost-archives . && docker run -p 8000:8000 --env-file .env the-lost-archives
```
