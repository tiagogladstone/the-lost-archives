#!/usr/bin/env python3
"""Upload video to YouTube using Data API v3."""

import os
import argparse
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service():
    import base64
    creds = None
    
    # Option 1: Check for YOUTUBE_TOKEN_JSON env var (base64 encoded, for Cloud Run)
    token_b64 = os.environ.get('YOUTUBE_TOKEN_JSON')
    if token_b64:
        try:
            token_json = base64.b64decode(token_b64).decode('utf-8')
            token_data = json.loads(token_json)
            creds = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes', SCOPES)
            )
            print("Using YouTube credentials from environment variable.")
        except Exception as e:
            print(f"Warning: Could not load credentials from env: {e}")
    
    # Option 2: Check for youtube_token.json file
    if not creds and os.path.exists('youtube_token.json'):
        creds = Credentials.from_authorized_user_file('youtube_token.json', SCOPES)
        print("Using YouTube credentials from youtube_token.json file.")
    
    # Option 3: Check for token.json file (legacy)
    if not creds and os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        print("Using YouTube credentials from token.json file.")
    
    # If still no credentials, error out (don't try interactive flow on server)
    if not creds:
        raise ValueError("No YouTube credentials found. Set YOUTUBE_TOKEN_JSON env var or provide youtube_token.json file.")
    
    # Refresh if needed
    if creds and creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
        print("Refreshed YouTube access token.")
    
    return build('youtube', 'v3', credentials=creds)

def upload_video(youtube, video_file, title, description, tags, language=None, category='22', privacy='unlisted'):
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags.split(',') if isinstance(tags, str) else tags,
            'categoryId': category  # 22 = People & Blogs
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False
        }
    }

    if language:
        body['snippet']['defaultAudioLanguage'] = language
        body['snippet']['defaultLanguage'] = language
    
    media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
    
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = request.execute()
    print(f"Video uploaded: https://youtu.be/{response['id']}")
    return response['id']

def upload_thumbnail(youtube, video_id, thumbnail_file):
    print(f"Uploading thumbnail {thumbnail_file} for video ID {video_id}...")
    try:
        request = youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_file)
        )
        response = request.execute()
        print(f"Thumbnail uploaded successfully: {response['items'][0]['default']['url']}")
    except Exception as e:
        print(f"An error occurred while uploading the thumbnail: {e}")

def main():
    parser = argparse.ArgumentParser(description="Upload a video to YouTube.")
    parser.add_argument('--video', required=True, help='Path to the video file.')
    parser.add_argument('--title', required=True, help='Title of the video.')
    parser.add_argument('--description', required=True, help='Description of the video.')
    parser.add_argument('--tags', default='', help='Comma-separated tags for the video.')
    parser.add_argument('--language', default=None, help='ISO 639-1 language code (e.g., en, pt-BR).')
    parser.add_argument('--privacy', default='unlisted', choices=['public', 'private', 'unlisted'], help='Privacy status of the video.')
    parser.add_argument('--thumbnail', default=None, help='Path to the thumbnail image file.')
    
    args = parser.parse_args()
    
    youtube = get_authenticated_service()
    video_id = upload_video(
        youtube, 
        args.video, 
        args.title, 
        args.description, 
        args.tags,
        language=args.language,
        privacy=args.privacy
    )
    
    if video_id and args.thumbnail:
        if os.path.exists(args.thumbnail):
            upload_thumbnail(youtube, video_id, args.thumbnail)
        else:
            print(f"Thumbnail file not found at {args.thumbnail}, skipping upload.")

    return video_id

if __name__ == '__main__':
    main()
