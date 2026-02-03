#!/usr/bin/env python3
"""Manual YouTube OAuth authorization (no browser required)."""
import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def main():
    flow = InstalledAppFlow.from_client_secrets_file(
        'client_secrets.json', SCOPES,
        redirect_uri='http://localhost')
    
    # Get authorization URL
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    print("\n" + "="*60)
    print("AUTORIZAÇÃO DO YOUTUBE")
    print("="*60)
    print("\n1. Abra este link no seu navegador:\n")
    print(auth_url)
    print("\n2. Faça login e autorize o acesso")
    print("3. Você será redirecionado para uma página com erro (localhost)")
    print("4. Copie a URL COMPLETA da barra de endereço e cole aqui:\n")
    
    redirect_response = input("Cole a URL aqui: ").strip()
    
    # Extract code from redirect URL
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(redirect_response)
        code = parse_qs(parsed.query)['code'][0]
        
        # Exchange code for credentials
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Save credentials
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes) if credentials.scopes else SCOPES
        }
        
        with open('youtube_token.json', 'w') as f:
            json.dump(token_data, f, indent=2)
        
        print("\n✅ Autorização concluída!")
        print("Token salvo em: youtube_token.json")
        print("\nAgora você pode fazer upload de vídeos para o YouTube!")
        
    except Exception as e:
        print(f"\n❌ Erro ao processar autorização: {e}")
        print("Tente novamente com a URL completa.")

if __name__ == '__main__':
    main()
