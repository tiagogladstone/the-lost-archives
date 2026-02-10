# API — FastAPI Server

## Framework

FastAPI com Pydantic models para validação. Servidor ASGI via Uvicorn.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/health` | Health check |
| POST | `/stories` | Criar nova story (cria jobs automaticamente) |
| GET | `/stories` | Listar stories |
| GET | `/stories/{id}` | Detalhe com scenes e jobs |
| GET | `/stories/{id}/review` | Dados para revisão (títulos + thumbnails) |
| POST | `/stories/{id}/review` | Submeter escolhas de título/thumbnail |
| POST | `/stories/{id}/publish` | Disparar publicação no YouTube |
| POST | `/stories/{id}/retry` | Reprocessar jobs falhados |
| DELETE | `/stories/{id}` | Deletar story e dados relacionados |

## Autenticação

API Key via header `X-API-Key`. Variável de ambiente: `API_KEY`.

## Modelos (models.py)

- `CreateStoryRequest` — topic, description, target_duration_minutes, languages
- `StoryResponse` — id, topic, status, timestamps
- `SceneResponse` — scene_order, text_content, image_url, audio_url, duration_seconds
- `StoryDetailResponse` — story + scenes + jobs
- `ReviewDataResponse` — title_options + thumbnail_options
- `TitleOptionResponse`, `ThumbnailOptionResponse` — opções de revisão
- `JobResponse` — status dos jobs

## Padrões

- Conexão direta com Supabase (client, não ORM)
- Se criação de jobs falhar, faz rollback da story (deleta)
- Story criada com status `generating_script` e primeiro job `generate_script`
- Jobs de scenes são criados pelo `script_worker`, não pela API

## Dependências

```
fastapi, uvicorn, supabase, pydantic, python-dotenv
```
