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
        
        # Check overall success
        overall_success = all(step['success'] for step in steps)
        
        return {
            'success': overall_success,
            'steps': steps,
            'output_dir': output_dir,
            'script_preview': script_content[:1000] + '...' if len(script_content) > 1000 else script_content,
            'script_length': len(script_content)
        }

def run_server():
    server = HTTPServer(('0.0.0.0', PORT), VideoGeneratorHandler)
    logger.info(f"Starting The Lost Archives server on port {PORT}")
    server.serve_forever()

if __name__ == '__main__':
    run_server()
