#!/usr/bin/env python3
"""One-time YouTube OAuth authorization."""
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    # Ensure the script looks for client_secrets.json in the project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    client_secrets_path = os.path.join(project_root, 'client_secrets.json')
    token_path = os.path.join(project_root, 'youtube_token.json')

    if not os.path.exists(client_secrets_path):
        print(f"❌ Erro: Arquivo '{client_secrets_path}' não encontrado.")
        print("Por favor, siga as instruções em YOUTUBE-SETUP.md para criá-lo.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        client_secrets_path, SCOPES)
    print("🌐 Abrindo o navegador para autorização do YouTube...")
    credentials = flow.run_local_server(port=8080)
    
    # Save credentials
    with open(token_path, 'w') as f:
        f.write(credentials.to_json())
    
    print(f"✅ Autorização concluída! Token salvo em {token_path}")

if __name__ == '__main__':
    main()
