# /Users/clawdbot/clawd/projects/the-lost-archives/workers/audio_worker.py
from workers.base_worker import BaseWorker
import os
import logging
import tempfile
import requests
import base64
import yaml
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class AudioWorker(BaseWorker):
    """
    Worker to generate TTS audio for a specific scene and upload it.
    """
    def __init__(self):
        super().__init__(job_type='generate_audio')
        self.voices_config = self._load_voices_config()
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set.")

    def _load_voices_config(self):
        """Loads the voice configuration from the YAML file."""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'voices.yaml')
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                logging.info(f"[{self.worker_id}] Loaded voices config from {config_path}")
                return yaml.safe_load(f)
        except FileNotFoundError:
            logging.error(f"[{self.worker_id}] Voice config file not found at {config_path}")
            raise
        except yaml.YAMLError as e:
            logging.error(f"[{self.worker_id}] Error parsing voice YAML file: {e}")
            raise

    def get_audio_duration(self, file_path):
        """Gets the duration of an audio file using ffprobe."""
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        try:
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return float(result.stdout)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logging.error(f"[{self.worker_id}] ffprobe failed: {e}. Ensure ffprobe is in your system's PATH.")
            raise Exception(f"Failed to get audio duration with ffprobe: {e}")


    def process(self, job):
        scene_id = job.get('scene_id')
        story_id = job.get('story_id')
        if not scene_id or not story_id:
            raise ValueError("Job data must include scene_id and story_id.")

        logging.info(f"[{self.worker_id}] Starting audio generation for scene_id: {scene_id}")

        # 1. Fetch scene and story data
        scene_res = self.supabase.table('scenes').select('text_content').eq('id', scene_id).single().execute()
        story_res = self.supabase.table('stories').select('languages').eq('id', story_id).single().execute()

        if not scene_res.data or not story_res.data:
            raise Exception(f"Scene {scene_id} or Story {story_id} not found.")
        
        text_content = scene_res.data['text_content']
        # Use the primary language for narration
        language = story_res.data['languages'][0] 
        
        if language not in self.voices_config:
            raise ValueError(f"Language '{language}' not found in voices configuration.")

        voice_info = self.voices_config[language]
        voice_name = voice_info['voice_name']
        language_code = voice_info['language_code']
        gender = voice_info.get('gender', 'MALE') # Default to MALE if not specified

        # 2. Generate TTS audio using Google Cloud TTS API
        tts_url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={self.api_key}"
        
        payload = {
            'input': {'text': text_content},
            'voice': {'languageCode': language_code, 'name': voice_name, 'ssmlGender': gender},
            'audioConfig': {'audioEncoding': 'MP3'}
        }
        
        logging.info(f"[{self.worker_id}] Requesting TTS from Google API for language {language}...")
        response = requests.post(tts_url, json=payload)
        response.raise_for_status()
        
        response_json = response.json()
        audio_content_b64 = response_json.get('audioContent')
        if not audio_content_b64:
            raise Exception(f"TTS API call succeeded but returned no audio content. Response: {response_json}")

        audio_data = base64.b64decode(audio_content_b64)

        # 3. Save to temp file, upload to storage, and get duration
        file_path = f"{story_id}/{scene_id}.mp3"
        duration_seconds = 0.0

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as temp_file:
            temp_file.write(audio_data)
            temp_file.flush() # Ensure all data is written to disk

            # Get duration
            duration_seconds = self.get_audio_duration(temp_file.name)
            logging.info(f"[{self.worker_id}] Generated audio with duration: {duration_seconds}s")
            
            # Upload
            temp_file.seek(0)
            logging.info(f"[{self.worker_id}] Uploading audio to Supabase Storage at: {file_path}")
            self.supabase.storage.from_('audio').upload(
                path=file_path,
                file=audio_data,
                file_options={"content-type": "audio/mpeg"}
            )

        # 4. Get public URL and update scene
        public_url_res = self.supabase.storage.from_('audio').get_public_url(file_path)
        audio_url = public_url_res
        
        logging.info(f"[{self.worker_id}] Updating scene {scene_id} with audio URL and duration.")
        self.supabase.table('scenes').update({
            'audio_url': audio_url,
            'duration_seconds': duration_seconds
        }).eq('id', scene_id).execute()

        logging.info(f"[{self.worker_id}] Successfully processed audio for scene {scene_id}.")

if __name__ == '__main__':
    logging.info("AudioWorker started. Polling for jobs...")
    worker = AudioWorker()
    worker.run()
