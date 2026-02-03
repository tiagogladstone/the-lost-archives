
import os
import subprocess
import tempfile
import shutil
import urllib.request
from workers.base_worker import BaseWorker
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

# Adiciona o diretório do projeto ao sys.path para importar scripts
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.render_video import render_video

class RenderWorker(BaseWorker):
    def __init__(self):
        super().__init__('render_video')

    def process(self, job):
        story_id = job['story_id']
        print(f"[{self.worker_id}] Processing render job for story_id: {story_id}")

        # 1. Busca TODAS as scenes da story
        scenes_res = self.supabase.table('scenes').select('image_url, audio_url, duration_seconds').eq('story_id', story_id).order('scene_order').execute()
        scenes = scenes_res.data
        if not scenes:
            raise Exception(f"No scenes found for story_id: {story_id}")

        # Cria diretório temporário para os arquivos
        with tempfile.TemporaryDirectory() as temp_dir:
            images_dir = os.path.join(temp_dir, 'images')
            audio_dir = os.path.join(temp_dir, 'audio')
            os.makedirs(images_dir)
            os.makedirs(audio_dir)

            # 2. Baixa imagens e áudios
            image_paths = []
            audio_paths = []
            total_duration = 0

            for i, scene in enumerate(scenes):
                # Download Image
                img_url = scene['image_url']
                img_ext = os.path.splitext(img_url)[1]
                img_path = os.path.join(images_dir, f"scene_{i:03d}{img_ext}")
                urllib.request.urlretrieve(img_url, img_path)
                image_paths.append(img_path)

                # Download Audio
                audio_url = scene['audio_url']
                audio_ext = os.path.splitext(audio_url)[1]
                audio_path = os.path.join(audio_dir, f"scene_{i:03d}{audio_ext}")
                urllib.request.urlretrieve(audio_url, audio_path)
                audio_paths.append(audio_path)
                total_duration += scene.get('duration_seconds', 5) # Fallback

            # 4. Concatena áudios
            narration_path = os.path.join(temp_dir, 'narration.mp3')
            file_list_path = os.path.join(temp_dir, "audio_files.txt")
            with open(file_list_path, 'w') as f:
                for path in audio_paths:
                    f.write(f"file '{os.path.abspath(path)}'\\n")
            
            concat_command = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', 
                '-i', file_list_path, '-c', 'copy', narration_path
            ]
            subprocess.run(concat_command, check=True, capture_output=True, text=True)

            # 5. Renderiza vídeo
            final_video_path = os.path.join(temp_dir, f"{story_id}.mp4")
            
            # O script render_video já aplica o Ken Burns
            render_video(
                clips_dir=images_dir,
                narration_path=narration_path,
                music_path="", # Sem música de fundo por enquanto
                output_path=final_video_path,
                resolution="1920x1080"
            )

            # 6. Upload do vídeo final para o Storage
            video_filename = f"{story_id}.mp4"
            storage_path = f"{story_id}/{video_filename}" # Salva em uma pasta com o ID da story
            
            with open(final_video_path, 'rb') as f:
                self.supabase.storage.from_('videos').upload(storage_path, f)

            video_url = self.supabase.storage.from_('videos').get_public_url(storage_path)

            print(f"[{self.worker_id}] Video uploaded to: {video_url}")

            # Atualiza story com a URL do vídeo
            self.supabase.table('stories').update({
                'video_url': video_url,
                'status': 'post_production' # Um status intermediário
            }).eq('id', story_id).execute()

            # 7. Cria jobs 'generate_thumbnails' e 'generate_metadata'
            self.supabase.table('jobs').insert([
                {'story_id': story_id, 'job_type': 'generate_thumbnails'},
                {'story_id': story_id, 'job_type': 'generate_metadata'}
            ]).execute()
            print(f"[{self.worker_id}] Created generate_thumbnails and generate_metadata jobs for story {story_id}.")

            # 8. NÃO chama check_and_advance aqui
            # Os próximos workers chamarão ao terminar

if __name__ == '__main__':
    worker = RenderWorker()
    worker.run()
