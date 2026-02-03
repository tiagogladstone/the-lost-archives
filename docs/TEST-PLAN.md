# Plano de Testes

Este documento descreve a estratégia de testes para garantir a robustez e a qualidade do pipeline SaaS do The Lost Archives.

## 1. Testes Unitários (por worker)

O objetivo dos testes unitários é verificar a lógica interna de cada worker isoladamente, mockando todas as dependências externas (APIs, banco de dados, storage).

### Worker: `script_worker`
- **O que testar:**
  - A formatação correta do prompt para a API Gemini.
  - A lógica de parsing que divide o roteiro em parágrafos (cenas).
  - O tratamento de uma resposta vazia ou malformada da API.
- **Como mockar dependências:**
  - Mockar a chamada `genai.Client.models.generate_content` para retornar um texto de roteiro pré-definido.
  - Mockar as chamadas ao `supabase_client` para simular a leitura da `story` e a escrita das `scenes`.
- **Comando para rodar:** `pytest workers/test_script_worker.py`

### Worker: `image_worker`
- **O que testar:**
  - A geração do prompt de imagem a partir do texto da cena.
  - A chamada correta para a API Imagen, incluindo `aspect_ratio` e `output_mime_type`.
  - A lógica de upload para o Supabase Storage.
- **Como mockar dependências:**
  - Mockar a API Gemini para a geração do prompt.
  - Mockar a API Imagen (`client.models.generate_images`) para retornar uma imagem falsa.
  - Mockar o `supabase_client.storage.from(...).upload` para simular o upload bem-sucedido.
- **Comando para rodar:** `pytest workers/test_image_worker.py`

### Worker: `audio_worker`
- **O que testar:**
  - A seleção correta da voz e idioma a partir do `config/voices.yaml`.
  - A chamada para a API Google TTS.
  - O cálculo da duração do áudio.
- **Como mockar dependências:**
  - Mockar a chamada `requests.post` para a API TTS para retornar um áudio falso em base64.
  - Mockar o `supabase_client.storage` para o upload.
  - Mockar `ffprobe` para simular a extração da duração.
- **Comando para rodar:** `pytest workers/test_audio_worker.py`

### Worker: `render_worker`
- **O que testar:**
  - A construção correta dos comandos `ffmpeg` e `ffprobe`.
  - A lógica de download dos arquivos de mídia do Storage.
  - A criação do arquivo de lista para concatenação.
- **Como mockar dependências:**
  - Mockar as chamadas de download do Supabase Storage para fornecer arquivos de imagem/áudio locais.
  - Mockar `subprocess.run` para verificar se os comandos `ffmpeg` são chamados com os argumentos corretos, sem executar o processo real (que é demorado).
- **Comando para rodar:** `pytest workers/test_render_worker.py`

### Worker: `upload_worker`
- **O que testar:**
  - A lógica de autenticação e refresh de token do YouTube.
  - A construção do corpo da requisição (`body`) para a API do YouTube.
  - A chamada para upload do vídeo e da thumbnail.
- **Como mockar dependências:**
  - Mockar `google.oauth2.credentials.Credentials` e `googleapiclient.discovery.build` para simular um serviço autenticado.
  - Mockar as chamadas `youtube.videos().insert()` e `youtube.thumbnails().set()`.
- **Comando para rodar:** `pytest workers/test_upload_worker.py`

## 2. Testes de Integração (entre workers)

O objetivo é testar a passagem de dados e o acionamento correto entre os workers, usando um banco de dados de teste real (local ou de staging).

- **Teste: Script → Image**
  - **Fluxo:** Rodar o `script_worker` para criar cenas no banco. Em seguida, rodar o `image_worker` para uma dessas cenas.
  - **Verificação:** Checar se o `image_worker` consegue ler a `text_content` criada pelo `script_worker` e popular a `image_url` corretamente na mesma entrada da tabela `scenes`.

- **Teste: Image + Audio → Render**
  - **Fluxo:** Para uma `story`, popular manualmente todas as `scenes` com `image_url` e `audio_url` válidos (podem apontar para arquivos de teste). Rodar o `render_worker`.
  - **Verificação:** O `render_worker` deve conseguir baixar todos os arquivos, renderizar um vídeo, e preencher a `video_url` na tabela `stories`.

- **Teste: Metadata + Thumb → Review**
  - **Fluxo:** Rodar `metadata_worker` e `thumbnail_worker` para uma `story` que está no estado `ready_for_review`.
  - **Verificação:** As tabelas `title_options` e `thumbnail_options` devem ser populadas com 3 entradas cada, e o campo `metadata` da `story` deve ser preenchido.

- **Teste: Review → Upload**
  - **Fluxo:** Chamar a API `POST /stories/{id}/publish` para uma `story` pronta para revisão.
  - **Verificação:** O `upload_worker` deve ser acionado, ler os dados corretos da `story` (título/thumb selecionados) e atualizar o status para `published`.

## 3. Teste E2E (fluxo completo)

Simula o uso real do sistema do início ao fim.

**Passo a passo para testar localmente:**
1.  **Criar story via API:**
    -   `curl -X POST http://localhost:8000/stories -H "Content-Type: application/json" -d '{"topic": "E2E Test: The Silk Road", "description": "...", "target_duration_minutes": 1}'`
2.  **Verificar cada fase:**
    -   **Fase 1:** Monitorar o banco até o status da `story` mudar para `producing` e as `scenes` serem criadas.
    -   **Fase 2:** Verificar se `image_url` e `audio_url` nas `scenes` são preenchidos.
    -   **Fase 3 (Render):** Verificar se o status muda para `ready_for_review` e se `video_url` é preenchido.
    -   **Fase 3 (Metadata):** Verificar a criação de `title_options` e `thumbnail_options`.
3.  **Fazer review no dashboard:**
    -   Acessar a UI (se disponível) ou simular as chamadas de API para selecionar um título e uma thumbnail.
    -   `curl -X POST http://localhost:8000/stories/{id}/select-title ...`
    -   `curl -X POST http://localhost:8000/stories/{id}/select-thumbnail ...`
4.  **Publicar:**
    -   `curl -X POST http://localhost:8000/stories/{id}/publish`
5.  **Verificar no YouTube:**
    -   Acessar o canal do YouTube e confirmar que o vídeo foi publicado com o título, descrição, tags e thumbnail corretos.

## 4. Teste de Falha e Retry

O objetivo é garantir que o sistema lida com falhas de forma graciosa.

-   **O que acontece se Imagen falha no meio?**
    -   **Teste:** Introduzir uma falha (ex: mockar a API para retornar erro 500) no `image_worker` para uma das cenas.
    - **Resultado esperado:** O job daquela cena deve ser marcado como `failed`. A `story` pode continuar processando outras cenas, mas não deve avançar para a fase de renderização até que todos os jobs de imagem e áudio sejam `completed`. A UI deve permitir um retry para o job falho.

-   **O que acontece se TTS falha?**
    -   **Teste:** Similar ao teste do Imagen, forçar um erro na API TTS.
    -   **Resultado esperado:** Idêntico ao do Imagen. O job de áudio falha, bloqueando a renderização.

-   **O que acontece se o render falha?**
    -   **Teste:** Forçar um erro no `ffmpeg` (ex: fornecer um arquivo de áudio corrompido).
    -   **Resultado esperado:** O `render_worker` deve capturar o erro, marcar o job de render como `failed` e atualizar o status da `story` principal para `failed` com uma mensagem de erro clara.

-   **Como funciona o retry?**
    -   O sistema deve ter um mecanismo (via API ou UI) para reenfileirar um job `failed`, mudando seu status para `queued`. A `story` associada deve voltar para um estado anterior (`producing` ou `rendering`) para permitir que o fluxo seja retomado após o sucesso do retry.

## 5. Testes de Performance

-   **Tempo esperado por worker (estimativas):**
    -   `script_worker`: < 30 segundos
    -   `image_worker` (por cena): ~15 segundos
    -   `audio_worker` (por cena): < 5 segundos
    -   `render_worker` (vídeo de 8 min): ~2-4 minutos
    -   `metadata/thumbnail_worker`: < 45 segundos
    -   `upload_worker`: Dependente da velocidade de upload, mas a lógica deve ser rápida.

-   **Tempo total esperado (do input ao `ready_for_review`):**
    -   Para um vídeo de 8 minutos com ~15 cenas, rodando a Fase 2 em paralelo, o tempo total esperado desde a criação até estar pronto para revisão deve ser em torno de **5 a 7 minutos**.
    -   `Script (30s) + (Máx(Imagem(15s), Áudio(5s)) * 15 cenas / N workers paralelos) + Render (3min)`
    -   Com paralelismo suficiente, o gargalo se torna a renderização.
