# Scripts — CLI Standalone

Scripts utilitários e versão legado dos workers. Cada script pode ser executado diretamente via CLI com argparse.

## Padrão

Todos os scripts seguem:
```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # ... args
    main(args)
```

## Scripts

| Script | Função |
|--------|--------|
| `generate_script.py` | Gera roteiro via Gemini |
| `generate_image.py` | Gera/busca imagens (Pexels + IA) — **importado por outros scripts/workers** |
| `generate_tts.py` | Text-to-speech (Google Cloud TTS) |
| `generate_tts_multi.py` | TTS multi-idioma |
| `generate_thumbnail.py` | Gera thumbnails |
| `generate_metadata.py` | Gera títulos, descrição, tags via Gemini |
| `generate_subtitles.py` | Gera legendas |
| `translate_content.py` | Traduz conteúdo via Gemini |
| `render_video.py` | Renderiza vídeo com FFmpeg |
| `fetch_media.py` | Download de vídeos/imagens do Pexels |
| `fetch_media_v2.py` | Versão v2 do fetch media |
| `apply_ken_burns.py` | Aplica efeito Ken Burns em imagens |
| `authorize_youtube.py` | Autorização OAuth YouTube |
| `authorize_youtube_manual.py` | Autorização manual YouTube |
| `upload_youtube.py` | Upload para YouTube |

## Notas

- `generate_image.py` é importado por outros scripts e workers como módulo
- `generate_thumbnail.py` tem `PEXELS_API_KEY` hardcoded — pendente de correção
- Scripts são usados pelo `main.py` (entrypoint HTTP legado) e por workers via import
- Configs lidas de `config/settings.yaml`, `config/voices.yaml`, `config/prompts.yaml`
