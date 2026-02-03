
import os
import tempfile
import urllib.request
from workers.base_worker import BaseWorker
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório do projeto ao sys.path para importar scripts
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.upload_youtube import get_authenticated_service, upload_video, upload_thumbnail

class UploadWorker(BaseWorker):
    def __init__(self):
        super().__init__('upload_youtube')

    def process(self, job):
        story_id = job['story_id']
        print(f"[{self.worker_id}] Processing upload job for story_id: {story_id}")

        # 1. Busca a story com todos os dados necessários
        story_res = self.supabase.table('stories').select(
            'selected_title, selected_thumbnail_url, video_url, metadata'
        ).eq('id', story_id).single().execute()
        
        story = story_res.data
        if not story:
            raise Exception(f"Story not found: {story_id}")
            
        # Validação
        required_fields = ['selected_title', 'selected_thumbnail_url', 'video_url', 'metadata']
        for field in required_fields:
            if not story.get(field):
                raise ValueError(f"Story {story_id} is missing required field '{field}' for upload.")
        if not story['metadata'].get('description') or not story['metadata'].get('tags'):
             raise ValueError(f"Story {story_id} metadata is incomplete.")

        with tempfile.TemporaryDirectory() as temp_dir:
            # 2. Baixa o vídeo
            print(f"[{self.worker_id}] Downloading video from {story['video_url']}")
            video_ext = os.path.splitext(story['video_url'])[1]
            local_video_path = os.path.join(temp_dir, f"video{video_ext}")
            urllib.request.urlretrieve(story['video_url'], local_video_path)
            
            # 3. Baixa a thumbnail
            print(f"[{self.worker_id}] Downloading thumbnail from {story['selected_thumbnail_url']}")
            thumb_ext = os.path.splitext(story['selected_thumbnail_url'])[1].split('?')[0] # Limpa query params
            local_thumb_path = os.path.join(temp_dir, f"thumbnail{thumb_ext}")
            urllib.request.urlretrieve(story['selected_thumbnail_url'], local_thumb_path)
            
            # 4. Reutiliza script para fazer o upload
            print(f"[{self.worker_id}] Authenticating with YouTube...")
            youtube_service = get_authenticated_service()
            
            title = story['selected_title']
            description = story['metadata']['description']
            tags = story['metadata']['tags']
            
            print(f"[{self.worker_id}] Uploading video to YouTube...")
            video_id = upload_video(
                youtube=youtube_service,
                video_file=local_video_path,
                title=title,
                description=description,
                tags=tags,
                privacy='unlisted' # Sempre sobe como não listado primeiro
            )
            
            if not video_id:
                raise Exception("Failed to upload video to YouTube.")
                
            print(f"[{self.worker_id}] Uploading thumbnail...")
            upload_thumbnail(
                youtube=youtube_service,
                video_id=video_id,
                thumbnail_file=local_thumb_path
            )

            # 5. Atualiza a story com o ID e URL do YouTube
            youtube_url = f"https://youtu.be/{video_id}"
            
            self.supabase.table('stories').update({
                'youtube_url': youtube_url,
                'youtube_video_id': video_id,
                'status': 'published' # 6. Atualiza status para 'published'
            }).eq('id', story_id).execute()
            
            print(f"[{self.worker_id}] Story {story_id} successfully published to {youtube_url}")

if __name__ == '__main__':
    worker = UploadWorker()
    worker.run()
