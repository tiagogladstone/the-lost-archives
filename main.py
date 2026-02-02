#!/usr/bin/env python3
"""Cloud Run entry point for The Lost Archives video generation."""

import os
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get('PORT', 8080))

class JobHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body)
            topic = data.get('topic', 'The mysteries of history')
            language = data.get('language', 'pt-BR')
            
            # Run the pipeline
            result = run_pipeline(topic, language)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
    
    def do_GET(self):
        # Health check
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'The Lost Archives - Video Generator')

def run_pipeline(topic: str, language: str) -> dict:
    """Execute the video generation pipeline."""
    import tempfile
    
    output_dir = tempfile.mkdtemp()
    
    steps = []
    
    # Step 1: Generate script
    script_path = f"{output_dir}/script.txt"
    result = subprocess.run([
        'python', 'scripts/generate_script.py',
        '--topic', topic,
        '--language', language,
        '--output', script_path
    ], capture_output=True, text=True)
    steps.append({'step': 'generate_script', 'success': result.returncode == 0, 'output': result.stdout[:500]})
    
    if result.returncode != 0:
        return {'success': False, 'steps': steps, 'error': result.stderr}
    
    # Step 2: Generate metadata
    metadata_path = f"{output_dir}/metadata.json"
    result = subprocess.run([
        'python', 'scripts/generate_metadata.py',
        '--topic', topic,
        '--languages', language,
        '--output', metadata_path
    ], capture_output=True, text=True)
    steps.append({'step': 'generate_metadata', 'success': result.returncode == 0})
    
    # Step 3: Generate TTS
    audio_path = f"{output_dir}/narration.mp3"
    result = subprocess.run([
        'python', 'scripts/generate_tts.py',
        '--input', script_path,
        '--language', language,
        '--output', audio_path
    ], capture_output=True, text=True)
    steps.append({'step': 'generate_tts', 'success': result.returncode == 0})
    
    # Return partial success for now (full pipeline would continue with media fetch and render)
    return {
        'success': True,
        'steps': steps,
        'output_dir': output_dir,
        'message': 'Pipeline executed (partial - TTS generated)'
    }

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), JobHandler)
    print(f"Starting server on port {PORT}")
    server.serve_forever()
