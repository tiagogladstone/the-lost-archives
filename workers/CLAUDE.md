# Workers — Job Queue Processors

## Padrão BaseWorker

Todos os workers herdam de `BaseWorker` (em `base_worker.py`) e implementam o método abstrato `process(job)`.

```python
class MeuWorker(BaseWorker):
    def __init__(self):
        super().__init__(job_type="meu_job_type")

    def process(self, job):
        # Lógica do worker
        pass
```

## Job Claiming

- Atômico via stored procedure `claim_next_job(p_job_type, p_worker_id)`
- Usa `FOR UPDATE SKIP LOCKED` para evitar race conditions
- BaseWorker faz polling automático buscando jobs disponíveis

## Retry

- Backoff exponencial: 30s → 60s → 120s
- Máximo 3 tentativas (`max_retries` na tabela jobs)
- Campo `next_retry_at` controla quando retentar

## Orquestração Descentralizada

Cada worker chama `check_and_advance()` ao completar um job, verificando se a story pode avançar de fase (ex: todos assets prontos → criar job render_video).

## Workers

| Worker | job_type | Fase | Dependência Externa |
|--------|----------|------|---------------------|
| ScriptWorker | `generate_script` | 1 | Gemini 1.5 Flash |
| ImageWorker | `generate_image` | 2 | Imagen 4 / Pexels |
| AudioWorker | `generate_audio` | 2 | Google Cloud TTS |
| TranslationWorker | `translate_scene` | 2 | Gemini |
| RenderWorker | `render_video` | 2 | FFmpeg |
| ThumbnailWorker | `generate_thumbnails` | 3 | Imagen 4 |
| MetadataWorker | `generate_metadata` | 3 | Gemini |
| UploadWorker | `upload_youtube` | 3 | YouTube Data API v3 |

## Storage (Supabase Buckets)

- `images/` — Imagens das cenas
- `audio/` — Áudios TTS
- `videos/` — Vídeos renderizados
- `thumbnails/` — Thumbnails geradas

## Execução

```bash
# Todos os workers (multiprocessing)
python worker_runner.py

# Worker individual
python -m workers.script_worker
```
