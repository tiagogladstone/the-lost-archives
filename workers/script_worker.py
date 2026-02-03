# /Users/clawdbot/clawd/projects/the-lost-archives/workers/script_worker.py
from workers.base_worker import BaseWorker
import google.generativeai as genai
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ScriptWorker(BaseWorker):
    """
    Worker to generate a script for a story, divide it into scenes,
    and create subsequent jobs for image, audio, and translation.
    """
    def __init__(self):
        super().__init__(job_type='generate_script')
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
        story_id = job['story_id']
        logging.info(f"[{self.worker_id}] Starting script generation for story_id: {story_id}")

        # 1. Fetch story details from Supabase
        story_res = self.supabase.table('stories').select('*').eq('id', story_id).single().execute()
        if not story_res.data:
            raise Exception(f"Story with id {story_id} not found.")
        
        story = story_res.data
        topic = story['topic']
        description = story.get('description', '')
        duration = story.get('target_duration_minutes', 8)
        languages = story.get('languages', ['en-US'])
        
        logging.info(f"[{self.worker_id}] Generating script for topic: '{topic}'")

        # 2. Generate script using Gemini
        model = genai.GenerativeModel('gemini-1.5-flash') # Using 1.5 flash as it's newer
        prompt = f"""Write a compelling narration script for a YouTube video about: {topic}
Context: {description}
Target duration: {duration} minutes (approximately {duration * 150} words)
Style: Documentary, engaging, mysterious

Write ONLY the narration text, divided into clear paragraphs.
Each paragraph will become a separate scene in the video.
Do not include any formatting like markdown, headers, or scene descriptions (e.g., "[SCENE START]").
Just write the plain text of the narration.
Ensure paragraphs are separated by a double newline.
"""
        
        response = model.generate_content(prompt)
        
        if not response.text or not response.text.strip():
             raise Exception("Failed to generate script: Gemini API returned an empty response.")

        script_text = response.text.strip()
        logging.info(f"[{self.worker_id}] Successfully generated script of length: {len(script_text)}")

        # 3. Split script into scenes (paragraphs)
        paragraphs = [p.strip() for p in script_text.split('\n\n') if p.strip()]
        if not paragraphs:
            raise Exception("Generated script content is empty after processing.")
        logging.info(f"[{self.worker_id}] Split script into {len(paragraphs)} scenes.")

        # 4. Update story with the full script and set status to 'producing'
        self.supabase.table('stories').update({
            'script_text': script_text,
            'status': 'producing'
        }).eq('id', story_id).execute()

        # 5. Create scenes and corresponding jobs in the database
        new_jobs = []
        for i, text in enumerate(paragraphs):
            scene_res = self.supabase.table('scenes').insert({
                'story_id': story_id,
                'scene_order': i + 1,
                'text_content': text
            }).execute()
            
            scene_id = scene_res.data[0]['id']
            
            # 6. Create image generation job for the scene
            new_jobs.append({
                'story_id': story_id,
                'scene_id': scene_id,
                'job_type': 'generate_image',
                'status': 'queued'
            })
            
            # 7. Create audio generation job for the scene
            new_jobs.append({
                'story_id': story_id,
                'scene_id': scene_id,
                'job_type': 'generate_audio',
                'status': 'queued'
            })
        
        # 8. Create translation jobs if extra languages are specified
        # The primary language is languages[0], so we translate to all others.
        if len(languages) > 1:
            # First, get all scene_ids we just created
            scenes_res = self.supabase.table('scenes').select('id').eq('story_id', story_id).execute()
            scene_ids = [s['id'] for s in scenes_res.data]

            for target_language in languages[1:]:
                for scene_id in scene_ids:
                    new_jobs.append({
                        'story_id': story_id,
                        'scene_id': scene_id,
                        'job_type': 'translate_scene',
                        'status': 'queued',
                        # Add target_language to the job payload, assuming the table has a 'payload' jsonb column
                        # Let's check the schema... no 'payload' column.
                        # For now, we'll have the translation_worker fetch the story to get the languages.
                        # A better approach would be to add a payload column to the jobs table.
                        # Let's stick to the current schema for this task.
                    })

        # Bulk insert all new jobs
        if new_jobs:
            self.supabase.table('jobs').insert(new_jobs).execute()
            logging.info(f"[{self.worker_id}] Created {len(new_jobs)} new jobs for story {story_id}.")

if __name__ == '__main__':
    logging.info("ScriptWorker started. Polling for jobs...")
    worker = ScriptWorker()
    worker.run()
