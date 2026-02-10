# Database — Supabase PostgreSQL

## Schema (schema.sql)

### Tabelas

**stories** — Tabela principal
- `id` UUID PK, `topic`, `description`, `target_duration_minutes`, `languages`
- `status`: pending | generating_script | producing | rendering | ready_for_review | publishing | published | failed
- `script_text`, `metadata` (JSONB)
- `selected_title`, `selected_thumbnail_url`, `youtube_url`, `youtube_video_id`
- `created_at`, `updated_at`

**scenes** — Cenas de uma story
- `id` UUID PK, `story_id` FK, `scene_order`
- `text_content`, `translated_text` (JSONB multi-idioma)
- `image_prompt`, `image_url`, `audio_url`, `duration_seconds`
- `status`

**jobs** — Fila de processamento
- `id` UUID PK, `story_id` FK, `scene_id` FK (opcional)
- `job_type`: generate_script | generate_image | generate_audio | translate_scene | render_video | generate_thumbnails | generate_metadata | upload_youtube
- `status`: queued | processing | completed | failed
- `worker_id`, `retry_count`, `max_retries`, `next_retry_at`
- `error_message`, timestamps

**title_options** — Opções de título para revisão
- `id` UUID PK, `story_id` FK, `title_text`

**thumbnail_options** — Opções de thumbnail para revisão
- `id` UUID PK, `story_id` FK, `image_url`, `feedback_history` (JSONB), `version`

### Stored Procedure

`claim_next_job(p_job_type, p_worker_id)` — Claiming atômico de jobs com `FOR UPDATE SKIP LOCKED`.

### Trigger

`set_stories_updated_at` — Atualiza `updated_at` automaticamente em stories.

### Índices

- `stories(status)`
- `jobs(status, job_type)`
- `scenes(story_id)`

### Foreign Keys

Cascade delete configurado: deletar story remove scenes, jobs, title_options e thumbnail_options.

## Storage Buckets

- `images/` — Imagens das cenas
- `audio/` — Áudios TTS
- `videos/` — Vídeos renderizados
- `thumbnails/` — Thumbnails geradas
