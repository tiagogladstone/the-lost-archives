# Config — Arquivos de Configuração YAML

## settings.yaml

Configurações gerais do projeto:
- `project_name`: "The Lost Archives"
- `default_language`: "en"
- `supported_languages`: ["en", "pt-br", "es"]
- `video_resolution`: "1920x1080"
- `music_volume`: 0.15
- `pexels_videos_per_keyword`: 3
- `gemini_model`: "gemini-1.5-flash"

## voices.yaml

Mapeamento de idioma para voz Google Cloud TTS (Wavenet):
- `en-US` → en-US-Wavenet-D
- `pt-BR` → pt-BR-Wavenet-B
- `es-ES` → es-ES-Wavenet-B

## prompts.yaml

Prompts de sistema para o Gemini:
- `generate_script` — Prompt para gerar roteiro de vídeo
- `translate_content` — Prompt para tradução
- `generate_metadata` — Prompt para títulos, descrição, tags YouTube
- `extract_keywords` — Prompt para extrair keywords de texto

## Convenções

- Adicionar novos idiomas requer entrada em `settings.yaml` (languages) e `voices.yaml` (voz TTS)
- Prompts do Gemini centralizados em `prompts.yaml` para fácil iteração
- Workers e scripts leem configs via `yaml.safe_load()`
