
import os
import json
from workers.base_worker import BaseWorker
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega variáveis de ambiente
load_dotenv()

class MetadataWorker(BaseWorker):
    def __init__(self):
        super().__init__('generate_metadata')
        self.genai_api_key = os.getenv("GOOGLE_API_KEY")
        if not self.genai_api_key:
            raise ValueError("GOOGLE_API_KEY must be set.")
        genai.configure(api_key=self.genai_api_key)
        self.genai_model = genai.GenerativeModel('gemini-1.5-pro-latest')

    def _generate_metadata_from_gemini(self, topic, script_text):
        """Gera títulos, descrição e tags a partir do Gemini."""
        print(f"[{self.worker_id}] Generating metadata for topic: {topic}")
        
        system_prompt = """
        You are a world-class YouTube SEO and content strategist. Your task is to generate viral, engaging, and SEO-optimized metadata for a video based on its topic and script.

        **Instructions:**
        1.  **Analyze the Content:** Deeply understand the provided topic and script to identify the core narrative, key entities, and emotional hooks.
        2.  **Generate 3 SEO-Optimized Titles:** Create three distinct titles. They must be catchy, create curiosity, and contain relevant keywords.
        3.  **Write a Compelling Description:** Craft a full, SEO-rich description (around 1200-1500 characters).
            *   Start with a strong, engaging hook that summarizes the video's core question.
            *   Naturally weave in primary and secondary keywords.
            *   Include logical sections with timestamps (e.g., 00:00 - Intro, 01:15 - The Discovery, etc.). YOU MUST INVENT PLAUSIBLE TIMESTAMPS.
            *   End with a call to action (subscribe, comment, etc.).
        4.  **Create Relevant Tags:** Generate a comma-separated string of relevant tags (both broad and specific). The total length of the string must not exceed 490 characters.
        5.  **Format the Output:** Return ONLY a single, valid JSON object with the following exact structure:
            {
              "titles": [
                "title 1",
                "title 2",
                "title 3"
              ],
              "description": "The full description text...",
              "tags": "tag1,tag2,tag3,another tag"
            }
        
        Do not include any other text, explanations, or markdown formatting like ```json. Your entire response must be ONLY the raw JSON object.
        """
        
        prompt = f"**Topic:** {topic}\\n**Script:**\\n{script_text[:4000]}" # Limita o script
        
        response = self.genai_model.generate_content(
            [system_prompt, prompt],
            generation_config=genai.types.GenerationConfig(
                temperature=0.8,
                max_output_tokens=4096,
                response_mime_type="application/json"
            )
        )
        
        try:
            # A API com response_mime_type="application/json" já deve retornar um JSON parseado
            return json.loads(response.text)
        except json.JSONDecodeError:
            print(f"[{self.worker_id}] Failed to decode JSON from Gemini. Raw response: {response.text}")
            raise Exception("Failed to get valid JSON from metadata generation.")
        except Exception as e:
            print(f"[{self.worker_id}] An unexpected error occurred: {e}")
            raise e

    def process(self, job):
        story_id = job['story_id']
        print(f"[{self.worker_id}] Processing metadata job for story_id: {story_id}")

        # 1. Busca story
        story_res = self.supabase.table('stories').select('topic, script_text').eq('id', story_id).single().execute()
        story = story_res.data
        if not story:
            raise Exception(f"Story not found: {story_id}")

        # 2. Usa Gemini para gerar metadados
        metadata = self._generate_metadata_from_gemini(story['topic'], story['script_text'])

        # Validação básica
        if not all(k in metadata for k in ['titles', 'description', 'tags']) or len(metadata['titles']) != 3:
            raise ValueError(f"Generated metadata is missing required fields or has incorrect title count. Got: {metadata}")

        # 3. Salva títulos em `title_options`
        title_records = [{'story_id': story_id, 'title_text': title} for title in metadata['titles']]
        self.supabase.table('title_options').insert(title_records).execute()
        print(f"[{self.worker_id}] Inserted 3 title options for story {story_id}.")

        # 4. Salva descrição e tags na story
        story_metadata = {
            'description': metadata['description'],
            'tags': metadata['tags']
        }
        self.supabase.table('stories').update({
            'metadata': story_metadata
        }).eq('id', story_id).execute()
        print(f"[{self.worker_id}] Updated story {story_id} with description and tags.")

        # 5. Chama check_and_advance
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
    worker = MetadataWorker()
    worker.run()
