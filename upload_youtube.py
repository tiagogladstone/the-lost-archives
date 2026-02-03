#!/usr/bin/env python3
"""
Uploads a video to YouTube using credentials stored in youtube_token.json.
"""
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
TOKEN_PATH = 'youtube_token.json'
CLIENT_SECRETS_PATH = 'client_secrets.json'

def get_authenticated_service():
    """Get an authenticated YouTube service object."""
    credentials = None
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, 'r') as token_file:
            creds_data = json.load(token_file)
        credentials = Credentials(
            token=creds_data['token'],
            refresh_token=creds_data.get('refresh_token'),
            token_uri=creds_data['token_uri'],
            client_id=creds_data['client_id'],
            client_secret=creds_data['client_secret'],
            scopes=creds_data['scopes']
        )

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("⏳ Token expirado. Atualizando...")
            credentials.refresh(Request())
        else:
            print("❌ Token inválido ou não encontrado.")
            print("Por favor, execute 'scripts/authorize_youtube.py' primeiro.")
            return None
    
    return build('youtube', 'v3', credentials=credentials)

def upload_video(youtube, file_path, title, description, tags, category_id="28"):
    """Uploads a video to YouTube."""
    if not os.path.exists(file_path):
        print(f"❌ Erro: Arquivo de vídeo não encontrado em '{file_path}'")
        return

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': 'private' # 'private', 'public', or 'unlisted'
        }
    }

    print(f"⬆️  Fazendo upload do vídeo: {title}...")
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"    Progresso do upload: {int(status.progress() * 100)}%")

    print(f"✅ Upload concluído! ID do vídeo: {response.get('id')}")
    print(f"   Link: https://www.youtube.com/watch?v={response.get('id')}")

def main():
    """Main function to test the upload."""
    youtube = get_authenticated_service()
    if not youtube:
        return

    # Example usage:
    # This part should be adapted to get video details from your pipeline
    video_file = 'path/to/your/video.mp4' # <-- CHANGE THIS
    video_title = "Test Title"
    video_description = "This is a test description."
    video_tags = ["test", "api", "upload"]
    
    if video_file == 'path/to/your/video.mp4':
        print("⚠️  Aviso: Altere o 'video_file' no script para um vídeo real.")
        return

    upload_video(youtube, video_file, video_title, video_description, video_tags)

if __name__ == '__main__':
    main()
