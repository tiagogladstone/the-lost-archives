-- Tabela principal: cada vídeo é uma "story"
CREATE TABLE stories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    topic TEXT NOT NULL,
    description TEXT,
    target_duration_minutes INTEGER DEFAULT 8,
    language TEXT NOT NULL DEFAULT 'en-US',
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending → generating_script → producing → rendering → ready_for_review → publishing → published → failed
    script_text TEXT,
    -- metadata contém: description (gerada), tags
    metadata JSONB DEFAULT '{}',
    selected_title TEXT,
    selected_thumbnail_url TEXT,
    youtube_url TEXT,
    youtube_video_id TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Cada story tem múltiplas cenas
CREATE TABLE scenes (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    scene_order INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    translated_text JSONB DEFAULT '{}', -- Ex: {"pt-BR": "texto traduzido", "es-ES": "texto traducido"}
    image_prompt TEXT,
    image_url TEXT,
    audio_url TEXT,
    duration_seconds FLOAT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Opções de título geradas para revisão humana
CREATE TABLE title_options (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    title_text TEXT NOT NULL,
    selected BOOLEAN DEFAULT FALSE,
    feedback_history JSONB DEFAULT '[]', -- Ex: [{"feedback": "troca mystery por secret", "timestamp": "...", "version": 2}]
    approved BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Opções de thumbnail geradas para revisão humana
CREATE TABLE thumbnail_options (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    selected BOOLEAN DEFAULT FALSE,
    feedback_history JSONB DEFAULT '[]',
    approved BOOLEAN DEFAULT FALSE,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fila de jobs para os workers (simplificada)
CREATE TABLE jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    -- Tipos: script, image, audio, translation, render, thumbnail, metadata, upload
    status TEXT NOT NULL DEFAULT 'queued',
    -- Status: queued → processing → completed → failed
    worker_id TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);


-- Índices
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_jobs_status_type ON jobs(status, job_type);
CREATE INDEX idx_scenes_story_id ON scenes(story_id);
CREATE INDEX idx_title_options_story_id ON title_options(story_id);
CREATE INDEX idx_thumbnail_options_story_id ON thumbnail_options(story_id);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_stories_updated_at
    BEFORE UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
