-- Tabela principal: cada vídeo é uma "story"
CREATE TABLE stories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    topic TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'en-US',
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending → generating_script → generating_images → generating_audio → generating_subtitles → generating_metadata → rendering → uploading → published → failed
    script_text TEXT,
    metadata JSONB DEFAULT '{}',
    -- metadata contém: title, description, tags, thumbnail_url
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
    -- Texto da narração desta cena
    image_prompt TEXT,
    image_url TEXT,
    -- URL no Supabase Storage
    audio_url TEXT,
    duration_seconds FLOAT,
    status TEXT NOT NULL DEFAULT 'pending',
    -- Status: pending → generating_image → image_done → generating_audio → audio_done → done
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Fila de jobs para os workers
CREATE TABLE jobs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    -- Tipos: generate_script, generate_images, generate_audio, generate_subtitles, generate_metadata, render_video, upload_youtube
    status TEXT NOT NULL DEFAULT 'queued',
    -- Status: queued → processing → completed → failed
    worker_id TEXT,
    payload JSONB DEFAULT '{}',
    result JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Assets (imagens, áudios, vídeos)
CREATE TABLE assets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    story_id UUID REFERENCES stories(id) ON DELETE CASCADE,
    scene_id UUID REFERENCES scenes(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL,
    -- Tipos: image, audio, video, thumbnail, subtitle
    file_path TEXT,
    storage_url TEXT,
    mime_type TEXT,
    size_bytes BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_stories_status ON stories(status);
CREATE INDEX idx_jobs_status ON jobs(status, job_type);
CREATE INDEX idx_jobs_story ON jobs(story_id);
CREATE INDEX idx_scenes_story ON scenes(story_id);

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER stories_updated_at
    BEFORE UPDATE ON stories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();