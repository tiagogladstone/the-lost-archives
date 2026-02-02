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
    # Check for existing credentials
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('client_secrets.json', SCOPES)
        creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
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

def main():
    parser = argparse.ArgumentParser(description="Upload a video to YouTube.")
    parser.add_argument('--video', required=True, help='Path to the video file.')
    parser.add_argument('--title', required=True, help='Title of the video.')
    parser.add_argument('--description', required=True, help='Description of the video.')
    parser.add_argument('--tags', default='', help='Comma-separated tags for the video.')
    parser.add_argument('--language', default=None, help='ISO 639-1 language code (e.g., en, pt-BR).')
    parser.add_argument('--privacy', default='unlisted', choices=['public', 'private', 'unlisted'], help='Privacy status of the video.')
    
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
    
    return video_id

if __name__ == '__main__':
    main()
