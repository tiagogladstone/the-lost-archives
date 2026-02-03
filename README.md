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

### Rendering with Music

To add background music to your videos, place your royalty-free music files (e.g., `.mp3`, `.wav`) into the `assets/music/` directory.

The rendering script can automatically mix one of these files into your video. Use the `--music` flag to specify the path to the audio file when running the render script manually or configuring the workflow.

**Example:**
```bash
python scripts/render_video.py \
  --clips_dir "path/to/clips" \
  --narration "path/to/narration.mp3" \
  --music "assets/music/your-track.mp3" \
  --output "final_video.mp4"
```

If the `--music` flag is omitted, the video will be rendered without background music.

#### Suggested Music Sources
- **YouTube Audio Library:** Free, high-quality music for creators.
- **Pixabay Music:** Free, royalty-free music library.
- **Epidemic Sound:** Paid subscription with a vast, high-quality catalog.
# Auto-deploy test Mon Feb  2 20:43:00 -03 2026
