# Database — Supabase PostgreSQL

## Schema (schema.sql)

### Tabelas

**stories** — Tabela principal
- `id` UUID PK, `topic`, `description`
- `status` TEXT DEFAULT 'draft'
- Status flow: draft → scripting → producing → rendering → post_production → ready_for_review → publishing → published | failed
- `target_duration_minutes` INTEGER DEFAULT 8
- `languages` JSONB DEFAULT '["en-US"]'
- `style` TEXT DEFAULT 'cinematic' (cinematic | anime | realistic | 3d)
- `aspect_ratio` TEXT DEFAULT '16:9' (16:9 | 9:16)
- `script_text`, `video_url`
- `youtube_url`, `youtube_video_id`
- `selected_title`, `selected_thumbnail_url`
- `metadata` JSONB DEFAULT '{}' ({description, tags})
- `error_message`
- `created_at`, `updated_at`

**scenes** — Cenas de uma story
- `id` UUID PK, `story_id` FK CASCADE, `scene_order`
- `text_content`, `translated_text` JSONB DEFAULT '{}' (multi-idioma: {"pt-BR": "texto", "es-ES": "texto"})
- `image_prompt`, `image_url`, `audio_url`, `duration_seconds`
- `created_at`

**title_options** — Opções de titulo para revisao
- `id` UUID PK, `story_id` FK CASCADE, `title_text`
- `created_at`

**thumbnail_options** — Opcoes de thumbnail para revisao
- `id` UUID PK, `story_id` FK CASCADE, `image_url`, `prompt`
- `created_at`

### Trigger

`update_updated_at_column()` — Funcao que seta `NOW()` no `updated_at`.
`set_stories_updated_at` — Trigger BEFORE UPDATE em stories que executa `update_updated_at_column()`.

### Indices

- `idx_stories_status` — stories(status)
- `idx_stories_created_at` — stories(created_at DESC)
- `idx_scenes_story_id` — scenes(story_id)
- `idx_scenes_story_order` — scenes(story_id, scene_order)
- `idx_title_options_story_id` — title_options(story_id)
- `idx_thumbnail_options_story_id` — thumbnail_options(story_id)

### Foreign Keys

Cascade delete configurado: deletar story remove scenes, title_options e thumbnail_options.

## Storage Buckets

- `images/` — Imagens das cenas (PNG)
- `audio/` — Audios TTS (MP3)
- `videos/` — Videos renderizados (MP4)
- `thumbnails/` — Thumbnails geradas (PNG)
