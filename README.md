# 🗃️ The Lost Archives

Automated YouTube channel for history and curiosities content.

## Features
- 🌍 Multi-language support (PT, EN, ES)
- 🤖 Fully automated video generation
- 🎙️ AI-powered narration (Google TTS)
- 📝 AI-generated scripts (Gemini)
- 🎬 Stock footage from Pexels
- 📊 A/B testing for titles/thumbnails

## Architecture
- **Orchestration:** GitHub Actions
- **Scripts:** Gemini 2.0 Flash
- **TTS:** Google Cloud Text-to-Speech
- **Media:** Pexels API
- **Rendering:** FFmpeg
- **Upload:** YouTube Data API

## Setup
See [docs/setup.md](docs/setup.md)

## Usage
```bash
# Generate a video
gh workflow run generate_video.yml -f topic="The History of Coffee"

# Upload to YouTube
gh workflow run upload_youtube.yml -f video_id="..."
```

## License
Private - All rights reserved
