# /Users/clawdbot/clawd/projects/the-lost-archives/workers/translation_worker.py
from workers.base_worker import BaseWorker
import google.generativeai as genai
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class TranslationWorker(BaseWorker):
    """
    Worker to translate scene text into additional languages.
    """
    def __init__(self):
        super().__init__(job_type='translate_scene')
        try:
            api_key = os.environ['GOOGLE_API_KEY']
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            logging.info(f"[{self.worker_id}] Gemini API configured successfully.")
        except (KeyError, ValueError) as e:
            logging.error(f"[{self.worker_id}] Failed to configure Gemini API: {e}")
            raise

    def process(self, job):
        scene_id = job.get('scene_id')
        story_id = job.get('story_id')
        if not scene_id or not story_id:
            raise ValueError("Job data must include scene_id and story_id.")
            
        logging.info(f"[{self.worker_id}] Starting translation for scene_id: {scene_id}")

        # 1. Fetch scene and story data
        scene_res = self.supabase.table('scenes').select('text_content, translated_text').eq('id', scene_id).single().execute()
        story_res = self.supabase.table('stories').select('languages').eq('id', story_id).single().execute()
        
        if not scene_res.data or not story_res.data:
            raise Exception(f"Scene {scene_id} or Story {story_id} not found.")

        text_content = scene_res.data['text_content']
        # The first language is the source, others are targets
        languages = story_res.data.get('languages', [])
        if len(languages) < 2:
            logging.warning(f"[{self.worker_id}] No target languages found for story {story_id}. Skipping translation.")
            return
        
        source_language = languages[0]
        target_languages = languages[1:]
        
        # Get existing translations or initialize a new dict
        translated_text_json = scene_res.data.get('translated_text') or {}
        if not isinstance(translated_text_json, dict):
             translated_text_json = {}


        # 2. Translate for each target language
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        for lang in target_languages:
            # Check if translation for this language already exists
            if lang in translated_text_json and translated_text_json[lang]:
                logging.info(f"[{self.worker_id}] Translation for '{lang}' already exists for scene {scene_id}. Skipping.")
                continue

            logging.info(f"[{self.worker_id}] Translating scene {scene_id} to '{lang}'")
            
            prompt = f"""
            Translate the following text from {source_language} to {lang}.
            Do not add any extra text, formatting, or explanations. Only output the translated text.

            Text to translate:
            "{text_content}"
            """
            
            response = model.generate_content(prompt)
            if response.text and response.text.strip():
                translated_text_json[lang] = response.text.strip()
            else:
                logging.warning(f"[{self.worker_id}] Gemini returned empty translation for scene {scene_id} to '{lang}'")

        # 3. Update the scene with the new translations
        if translated_text_json:
            logging.info(f"[{self.worker_id}] Updating scene {scene_id} with new translations.")
            self.supabase.table('scenes').update({
                'translated_text': translated_text_json
            }).eq('id', scene_id).execute()

        # NOTE: The translation worker doesn't advance the state on its own.
        # The state is advanced by image_worker and audio_worker completing.
        # So we don't call check_and_advance here.

if __name__ == '__main__':
    logging.info("TranslationWorker started. Polling for jobs...")
    worker = TranslationWorker()
    worker.run()
