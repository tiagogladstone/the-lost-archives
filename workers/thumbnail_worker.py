
import os
import tempfile
import uuid
from workers.base_worker import BaseWorker
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório do projeto ao sys.path para importar scripts
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.generate_image import generate_image

class ThumbnailWorker(BaseWorker):
    def __init__(self):
        super().__init__('generate_thumbnails')
        self.genai_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.genai_api_key:
            raise ValueError("GOOGLE_API_KEY must be set.")
        genai.configure(api_key=self.genai_api_key)
        self.genai_model = genai.GenerativeModel('gemini-1.5-pro-latest')

    def _generate_thumbnail_prompts(self, topic, script_text):
        """Gera 3 prompts de thumbnail usando Gemini."""
        print(f"[{self.worker_id}] Generating thumbnail prompts for topic: {topic}")
        
        system_prompt = """
        You are an expert in creating viral YouTube thumbnails. Your task is to generate 3 distinct, compelling, and visually striking thumbnail prompts based on a video's topic and script.

        **Instructions:**
        1.  **Analyze the Core Idea:** Read the topic and script to understand the central theme, key moments, and emotional hooks.
        2.  **Think Visually:** Brainstorm strong visual concepts that are intriguing and easy to understand at a small size. Use bold colors, high contrast, and clear subjects.
        3.  **Incorporate Text (Sparingly):** Suggest short, bold, high-impact text (2-5 words) to overlay on the image. This text should create curiosity or state a bold claim.
        4.  **Create 3 DIVERSE Options:** Provide three different angles or styles. For example:
            *   **Option 1 (Symbolic/Abstract):** A powerful metaphor or symbol representing the theme.
            *   **Option 2 (Action/Climax):** A depiction of a key event or conflict from the story.
            *   **Option 3 (Human/Emotional):** Focus on a human figure's reaction or a mysterious character.
        5.  **Format the Output:** Return ONLY a list of 3 strings, where each string is a detailed prompt for an image generation model like Imagen 4. Do not include any other text, titles, or explanations. Each prompt must be a single line.
        
        **Example Input:**
        Topic: The Lost City of Atlantis
        Script: ...a story about a technologically advanced civilization that vanished beneath the waves...
        
        **Example Output (as raw text, one prompt per line):**
        A massive, glowing blue crystal powering a futuristic city, moments before it's engulfed by a giant tidal wave. Text: "THE DAY IT VANISHED". Dramatic, cinematic lighting.
        An ancient explorer looking at a holographic map showing a sunken city, a look of shock on his face. The map glows brightly in a dark cavern. Text: "IT WAS REAL?". High contrast, mysterious.
        A beautiful, ornate trident weapon lying half-buried in the sand on a dark ocean floor, with the faint ruins of a massive city visible in the murky background. Text: "THEIR FINAL MISTAKE". Photorealistic, underwater.
        """
        
        prompt = f"**Topic:** {topic}\\n**Script:**\\n{script_text[:1500]}" # Limita o script para economizar tokens
        
        response = self.genai_model.generate_content(
            [system_prompt, prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=0.9,
                max_output_tokens=1024,
            )
        )
        
        prompts = [p.strip() for p in response.text.split('\\n') if p.strip()]
        if len(prompts) < 3:
             raise Exception(f"Gemini generated only {len(prompts)} prompts, expected 3.")
        return prompts[:3]


    def process(self, job):
        story_id = job['story_id']
        print(f"[{self.worker_id}] Processing thumbnail job for story_id: {story_id}")

        # 1. Busca story
        story_res = self.supabase.table('stories').select('topic, script_text').eq('id', story_id).single().execute()
        story = story_res.data
        if not story:
            raise Exception(f"Story not found: {story_id}")

        # 2. Gera 3 prompts
        prompts = self._generate_thumbnail_prompts(story['topic'], story['script_text'])

        with tempfile.TemporaryDirectory() as temp_dir:
            for i, prompt in enumerate(prompts):
                print(f"[{self.worker_id}] Generating thumbnail {i+1}/3 for story {story_id}")
                
                # 3. Gera imagem
                img_filename = f"thumb_{uuid.uuid4()}.png"
                local_img_path = os.path.join(temp_dir, img_filename)
                
                # Reutiliza o script para gerar a imagem
                generate_image(prompt, local_img_path, style="cinematic, high contrast, bold text")

                # 4. Upload para Storage
                storage_path = f"{story_id}/{img_filename}"
                with open(local_img_path, 'rb') as f:
                    self.supabase.storage.from_('thumbnails').upload(storage_path, f, {'content-type': 'image/png'})
                
                image_url = self.supabase.storage.from_('thumbnails').get_public_url(storage_path)

                # 5. Cria entrada em `thumbnail_options`
                self.supabase.table('thumbnail_options').insert({
                    'story_id': story_id,
                    'image_url': image_url,
                    'prompt': prompt
                }).execute()
                print(f"[{self.worker_id}] Uploaded thumbnail {i+1} to {image_url}")

        # 6. Chama check_and_advance para verificar se a metadata também está pronta
        # Esta função precisa ser aprimorada para checar o status dos jobs de metadata.
        # Por enquanto, vamos assumir que ela faz a verificação correta.
        self.check_and_advance_post_render(story_id)

    def check_and_advance_post_render(self, story_id):
        """Verifica se tanto thumbnails quanto metadata estão prontos."""
        print(f"[{self.worker_id}] Checking if story {story_id} can be moved to 'ready_for_review'.")
        
        # Verifica se as 3 thumbnails existem
        thumbs_res = self.supabase.table('thumbnail_options').select('id', count='exact').eq('story_id', story_id).execute()
        
        # Verifica se os metadados (títulos) existem
        titles_res = self.supabase.table('title_options').select('id', count='exact').eq('story_id', story_id).execute()

        if thumbs_res.count >= 3 and titles_res.count >= 3:
            print(f"[{self.worker_id}] Both thumbnails and metadata are ready for story {story_id}. Advancing to 'ready_for_review'.")
            self.supabase.table('stories').update({
                'status': 'ready_for_review'
            }).eq('id', story_id).execute()
        else:
            print(f"[{self.worker_id}] Story {story_id} is not ready. Thumbs: {thumbs_res.count}, Titles: {titles_res.count}.")


if __name__ == '__main__':
    worker = ThumbnailWorker()
    worker.run()
