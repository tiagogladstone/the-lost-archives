#!/usr/bin/env python3
"""Cloud Run entry point for The Lost Archives video generation."""

import os
import json
import logging
import tempfile
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

PORT = int(os.environ.get('PORT', 8080))

class VideoGeneratorHandler(BaseHTTPRequestHandler):
    
    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())
    
    def do_GET(self):
        path = urlparse(self.path).path
        
        if path == '/' or path == '/health':
            self.send_json({'status': 'healthy', 'service': 'The Lost Archives'})
        elif path == '/status':
            self.send_json({
                'status': 'running',
                'version': '1.0.0',
                'endpoints': ['/', '/health', '/status', '/generate']
            })
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def do_POST(self):
        path = urlparse(self.path).path
        
        if path == '/generate' or path == '/':
            self.handle_generate()
        else:
            self.send_json({'error': 'Not found'}, 404)
    
    def handle_generate(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body) if body else {}
            
            topic = data.get('topic', 'The mysteries of history')
            language = data.get('language', 'pt-BR')
            
            logger.info(f"Generating content for topic: {topic}, language: {language}")
            
            result = self.run_pipeline(topic, language)
            self.send_json(result)
            
        except json.JSONDecodeError as e:
            self.send_json({'error': f'Invalid JSON: {str(e)}'}, 400)
        except Exception as e:
            logger.error(f"Error in generate: {str(e)}")
            self.send_json({'error': str(e)}, 500)
    
    def run_pipeline(self, topic, language):
        output_dir = tempfile.mkdtemp()
        steps = []
        
        # Step 1: Generate script
        script_path = f"{output_dir}/script.txt"
        result = subprocess.run([
            'python', 'scripts/generate_script.py',
            '--topic', topic,
            '--language', language,
            '--output', script_path
        ], capture_output=True, text=True, timeout=120)
        
        script_success = result.returncode == 0
        steps.append({
            'step': 'generate_script',
            'success': script_success,
            'output': result.stdout[:500] if script_success else result.stderr[:500]
        })
        
        if not script_success:
            return {'success': False, 'steps': steps, 'error': 'Script generation failed'}
        
        # Read generated script
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        # Step 2: Generate metadata
        metadata_path = f"{output_dir}/metadata.json"
        result = subprocess.run([
            'python', 'scripts/generate_metadata.py',
            '--topic', topic,
            '--languages', language,
            '--output', metadata_path
        ], capture_output=True, text=True, timeout=60)
        
        steps.append({
            'step': 'generate_metadata',
            'success': result.returncode == 0
        })
        
        # Step 3: Generate TTS
        audio_path = f"{output_dir}/narration.mp3"
        result = subprocess.run([
            'python', 'scripts/generate_tts.py',
            '--input', script_path,
            '--language', language,
            '--output', audio_path
        ], capture_output=True, text=True, timeout=300)
        
        tts_success = result.returncode == 0
        steps.append({
            'step': 'generate_tts',
            'success': tts_success,
            'output': result.stdout[:1000] if tts_success else result.stderr[:1000]
        })
        
        if not tts_success:
            return {'success': False, 'steps': steps, 'error': 'TTS generation failed'}

        # Step 4: Fetch media from Pexels
        clips_dir = f"{output_dir}/clips"
        result = subprocess.run([
            'python', 'scripts/fetch_media.py',
            '--script', script_path,
            '--output', clips_dir
        ], capture_output=True, text=True, timeout=300)

        fetch_success = result.returncode == 0
        steps.append({
            'step': 'fetch_media',
            'success': fetch_success,
            'output': result.stdout[:1000] if fetch_success else result.stderr[:1000]
        })

        if not fetch_success:
            return {'success': False, 'steps': steps, 'error': 'Media fetching failed'}

        # Step 5: Render final video
        video_path = f"{output_dir}/final_video.mp4"
        result = subprocess.run([
            'python', 'scripts/render_video.py',
            '--clips_dir', clips_dir,
            '--narration', audio_path,
            '--output', video_path
        ], capture_output=True, text=True, timeout=600)
        
        render_success = result.returncode == 0
        steps.append({
            'step': 'render_video',
            'success': render_success,
            'output': result.stdout[:1000] if render_success else result.stderr[:1000]
        })

        if not render_success:
            return {'success': False, 'steps': steps, 'error': 'Video rendering failed'}
        
        # Step 6: Upload to YouTube
        youtube_url = None
        try:
            # Read metadata for title/description
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            lang_metadata = metadata.get(language, {})
            
            # Use the 'direct' title for better SEO, fallback to topic
            title = lang_metadata.get('titles', {}).get('direct', topic)[:100]
            description = lang_metadata.get('description', f'Video about {topic}')
            tags = ','.join(lang_metadata.get('tags', [topic]))
            
            # Check for a generated thumbnail
            thumbnail_path = f"{output_dir}/thumbnail.jpg"
            
            upload_command = [
                'python', 'scripts/upload_youtube.py',
                '--video', video_path,
                '--title', title,
                '--description', description,
                '--tags', tags,
                '--language', language, # Pass full language code
                '--privacy', 'unlisted'
            ]
            
            if os.path.exists(thumbnail_path):
                upload_command.extend(['--thumbnail', thumbnail_path])

            result = subprocess.run(upload_command, capture_output=True, text=True, timeout=600)
            
            upload_success = result.returncode == 0
            
            # Extract YouTube URL from output
            if upload_success and 'youtu.be/' in result.stdout:
                import re
                match = re.search(r'https://youtu\.be/[\w-]+', result.stdout)
                if match:
                    youtube_url = match.group(0)
            
            steps.append({
                'step': 'upload_youtube',
                'success': upload_success,
                'output': result.stdout[:500] if upload_success else result.stderr[:500],
                'youtube_url': youtube_url
            })
        except Exception as e:
            steps.append({
                'step': 'upload_youtube',
                'success': False,
                'output': str(e)
            })
        
        # Check overall success
        overall_success = all(step['success'] for step in steps)
        
        return {
            'success': overall_success,
            'steps': steps,
            'output_dir': output_dir,
            'video_path': video_path,
            'youtube_url': youtube_url,
            'script_preview': script_content[:1000] + '...' if len(script_content) > 1000 else script_content,
            'script_length': len(script_content)
        }

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), VideoGeneratorHandler)
    logger.info(f"Starting The Lost Archives server on port {PORT}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
