-- The Lost Archives v2 — Schema Simplificado
-- Sem tabela jobs, sem polling. Pipeline orquestrado por código Python.

-- ============================================
-- TABELAS
-- ============================================

CREATE TABLE stories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    topic TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    -- Status flow: draft → scripting → producing → rendering → post_production → ready_for_review → publishing → published | failed
    target_duration_minutes INTEGER DEFAULT 8,
    languages JSONB DEFAULT '["en-US"]',
    style TEXT DEFAULT 'cinematic',          -- cinematic | anime | realistic | 3d
    aspect_ratio TEXT DEFAULT '16:9',        -- 16:9 | 9:16
    script_text TEXT,
    video_url TEXT,
    youtube_url TEXT,
    youtube_video_id TEXT,
    selected_title TEXT,
    selected_thumbnail_url TEXT,
    metadata JSONB DEFAULT '{}',             -- {description, tags}
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE scenes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    scene_order INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    translated_text JSONB DEFAULT '{}',      -- {"pt-BR": "texto", "es-ES": "texto"}
    image_prompt TEXT,
    image_url TEXT,
    audio_url TEXT,
    duration_seconds FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE title_options (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    title_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE thumbnail_options (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    prompt TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- TRIGGER: updated_at automático em stories
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_stories_updated_at
    BEFORE UPDATE ON stories
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- ÍNDICES
-- ============================================

CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_stories_created_at ON stories(created_at DESC);
CREATE INDEX idx_scenes_story_id ON scenes(story_id);
CREATE INDEX idx_scenes_story_order ON scenes(story_id, scene_order);
CREATE INDEX idx_title_options_story_id ON title_options(story_id);
CREATE INDEX idx_thumbnail_options_story_id ON thumbnail_options(story_id);

-- ============================================
-- STORAGE BUCKETS (criar manualmente no Supabase Dashboard)
-- ============================================
-- images/      — Imagens das cenas (PNG)
-- audio/       — Áudios TTS (MP3)
-- videos/      — Vídeos renderizados (MP4)
-- thumbnails/  — Thumbnails geradas (PNG)
