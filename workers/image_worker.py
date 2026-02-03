# /Users/clawdbot/clawd/projects/the-lost-archives/workers/image_worker.py
from workers.base_worker import BaseWorker
import google.generativeai as genai
import os
import logging
import tempfile
from google.genai.types import GenerateImagesConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ImageWorker(BaseWorker):
    """
    Worker to generate an image for a specific scene based on its text content.
    """
    def __init__(self):
        super().__init__(job_type='generate_image')
        try:
            api_key = os.environ['GOOGLE_API_KEY']
            if not api_key:
                raise ValueError("GOOGLE_API_KEY environment variable not set.")
            genai.configure(api_key=api_key)
            logging.info(f"[{self.worker_id}] Gemini/Imagen API configured successfully.")
        except (KeyError, ValueError) as e:
            logging.error(f"[{self.worker_id}] Failed to configure Gemini/Imagen API: {e}")
            raise

    def process(self, job):
        scene_id = job.get('scene_id')
        story_id = job.get('story_id')
        if not scene_id or not story_id:
            raise ValueError("Job data must include scene_id and story_id.")

        logging.info(f"[{self.worker_id}] Starting image generation for scene_id: {scene_id}")

        # 1. Fetch scene content
        scene_res = self.supabase.table('scenes').select('text_content').eq('id', scene_id).single().execute()
        if not scene_res.data:
            raise Exception(f"Scene with id {scene_id} not found.")
        text_content = scene_res.data['text_content']

        # 2. Generate a detailed image prompt using Gemini
        prompt_model = genai.GenerativeModel('gemini-1.5-flash')
        prompt_template = f"""
        Based on the following narration text from a historical documentary, create a single, detailed, and vivid prompt for an AI image generator (like Imagen 4).
        The image should be cinematic, photorealistic, and capture the mood of the scene. Avoid text, logos, or watermarks.
        Focus on creating a visually stunning and historically evocative scene. Specify camera angles, lighting, and composition.

        Narration Text: "{text_content}"

        Image Prompt:
        """
        prompt_response = prompt_model.generate_content(prompt_template)
        image_prompt = prompt_response.text.strip()
        logging.info(f"[{self.worker_id}] Generated image prompt: {image_prompt}")

        # 3. Generate image using Imagen 4
        logging.info(f"[{self.worker_id}] Calling Imagen 4 API...")
        image_model = "imagen-3.0-generate-001" # Using Imagen 3 as per latest available models
        image_response = genai.generate_images(
            model=image_model,
            prompt=image_prompt,
            config=GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                output_mime_type="image/png",
            ),
        )

        if not image_response.generated_images:
            raise Exception("Image generation failed. No images were returned from the API.")
        
        generated_image = image_response.generated_images[0]
        
        # 4. Upload image to Supabase Storage
        file_path = f"{story_id}/{scene_id}.png"
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as temp_file:
            generated_image.image.save(temp_file.name)
            temp_file.seek(0)
            
            logging.info(f"[{self.worker_id}] Uploading image to Supabase Storage at: {file_path}")
            
            # The official library has some issues with `upload_file`.
            # We'll use the raw postgrest/storage API via the client.
            self.supabase.storage.from_('images').upload(
                path=file_path,
                file=temp_file,
                file_options={"content-type": "image/png"}
            )

        # 5. Get public URL and update scene
        public_url_res = self.supabase.storage.from_('images').get_public_url(file_path)
        image_url = public_url_res
        
        logging.info(f"[{self.worker_id}] Updating scene {scene_id} with image URL and prompt.")
        self.supabase.table('scenes').update({
            'image_url': image_url,
            'image_prompt': image_prompt
        }).eq('id', scene_id).execute()

        logging.info(f"[{self.worker_id}] Successfully processed image for scene {scene_id}.")
        # The check_and_advance logic will be called by the base worker's run loop

if __name__ == '__main__':
    logging.info("ImageWorker started. Polling for jobs...")
    worker = ImageWorker()
    worker.run()
