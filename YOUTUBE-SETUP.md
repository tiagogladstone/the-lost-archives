# Configuração de Acesso para Uploads no YouTube

Siga estes passos para gerar as credenciais necessárias para que o sistema possa fazer upload de vídeos para o canal The Lost Archives.

## Passo 1: Habilitar a API do YouTube

1.  Acesse o [Console de APIs do Google](https://console.cloud.google.com/apis/library?project=project-75d9e1c4-e2a7-4da9-923).
2.  Na barra de busca, digite "**YouTube Data API v3**" e selecione-a.
3.  Verifique se a API está habilitada. Se o botão disser "**Manage**", ela já está ativa. Se disser "**Enable**", clique nele para ativá-la.

## Passo 2: Criar Credenciais OAuth 2.0

1.  Acesse a [página de Credenciais](https://console.cloud.google.com/apis/credentials?project=project-75d9e1c4-e2a7-4da9-923).
2.  Clique em **"+ CREATE CREDENTIALS"** na parte superior e selecione **"OAuth client ID"**.
3.  Em **"Application type"**, selecione **"Desktop app"**.
4.  No campo **"Name"**, digite `The Lost Archives Uploader`.
5.  Clique em **"CREATE"**.
6.  Uma janela aparecerá com seu Client ID e Client Secret. Clique em **"DOWNLOAD JSON"**.
7.  Salve este arquivo na raiz do projeto com o nome `client_secrets.json`.

**MUITO IMPORTANTE:** Este arquivo é secreto e não deve ser compartilhado ou enviado para o GitHub.

## Passo 3: Autorizar o Acesso à Conta

## Passo 3: Autorizar o Acesso à Conta

Agora que a API está habilitada e as credenciais foram baixadas, você precisa executar um script para autorizar o acesso à conta do YouTube pela primeira vez.

1.  Abra um terminal no diretório do projeto.
2.  Certifique-se de ter as bibliotecas Python necessárias instaladas:
    ```bash
    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
    ```
3.  Execute o script de autorização:
    ```bash
    python3 scripts/authorize_youtube.py
    ```
4.  O script abrirá uma janela no seu navegador. Faça login com a conta do YouTube do canal **@TheLostArchives-g3t**.
5.  Conceda as permissões solicitadas.
6.  Após a autorização, você verá uma mensagem de sucesso no terminal, e um arquivo `youtube_token.json` será criado na raiz do projeto.

Com isso, a configuração está completa. O sistema agora pode fazer uploads para o YouTube em seu nome.
