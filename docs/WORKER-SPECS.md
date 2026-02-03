# Worker Specifications

Este documento detalha a especificação de cada worker no pipeline de SaaS do The Lost Archives.

---

## Worker: `script_worker`

### Função
Gera o roteiro completo de uma história e o divide em cenas individuais.

### Fase
Fase 1 (Sequencial).

### Script Reutilizado
`scripts/generate_script.py`
- Lógica do prompt para o Gemini, especificando o estilo narrativo e a estrutura.
- Chamada para a API `genai` para gerar o conteúdo do roteiro.

### Input
- **Lê da tabela `stories`:**
  - `id` (story_id)
  - `topic`
  - `description`
  - `target_duration_minutes`
- **Exemplo concreto de input (do job):**
  ```json
  {
    "story_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
    "topic": "The Great Library of Alexandria",
    "description": "A deep dive into the history and destruction of the ancient world's greatest collection of knowledge.",
    "target_duration_minutes": 8
  }
  ```

### Output Esperado
- **Escreve na tabela `stories`:**
  - `script_text`: O roteiro completo gerado.
  - `status`: Atualiza para `producing`.
- **Cria na tabela `scenes`:**
  - Múltiplas entradas, uma para cada parágrafo do roteiro, com `story_id`, `scene_order`, e `text_content`.
- **Exemplo concreto de output (no banco):**
  - **stories:** `script_text` preenchido, `status` = 'producing'.
  - **scenes:**
    ```json
    [
      {"story_id": "a1b2...", "scene_order": 1, "text_content": "In the heart of ancient Egypt, nestled by the shimmering Mediterranean, stood a beacon of human intellect: the Great Library of Alexandria..."},
      {"story_id": "a1b2...", "scene_order": 2, "text_content": "Founded by Ptolemy I Soter, a successor to Alexander the Great, it was more than a library; it was a research institution..."},
      {"story_id": "a1b2...", "scene_order": 3, "text_content": "It is said to have housed over 400,000 scrolls, containing the collective wisdom of civilizations from Greece to Persia..."}
    ]
    ```

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### Dependências
- **Depende de:** Nenhum worker (é o primeiro).
- **Dispara:** `image_worker`, `audio_worker`, `translation_worker` (indiretamente, ao mudar o status da story para `producing`).

### Teste Local
```bash
# 1. Configurar env vars
export SUPABASE_URL="YOUR_SUPABASE_URL"
export SUPABASE_KEY="YOUR_SUPABASE_SERVICE_KEY"
export GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"

# 2. Inserir dados de teste no banco
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('stories').insert({'topic': 'Test Topic', 'description': 'Test Desc', 'status': 'generating_script'}).execute(); print(data[1][0]['id'])"

# 3. Rodar o worker (simulado, pois ele opera em loop)
# Assumindo que o worker pegue a story criada acima
python workers/script_worker.py --story-id <ID_DA_STORY_ACIMA>

# 4. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('scenes').select('*').eq('story_id', '<ID_DA_STORY_ACIMA>').execute(); assert len(data[1]) > 0; print('Success!')"
```

### Critérios de Aceite
- [ ] Ao final da execução, o status da `story` deve ser `producing`.
- [ ] A tabela `scenes` deve conter pelo menos 10 registros associados à `story_id`.
- [ ] O campo `script_text` na tabela `stories` não deve estar vazio.

### Possíveis Erros
- **API do Gemini falha:** O worker deve registrar o erro no job, atualizar o status da `story` para `failed` com a mensagem de erro da API.
- **Roteiro vazio ou inválido:** Se a API retornar um texto vazio, o worker deve falhar e registrar o erro, evitando a criação de cenas vazias.

---

## Worker: `image_worker`

### Função
Gera uma imagem para cada cena da história.

### Fase
Fase 2 (Paralelo).

### Script Reutilizado
- `scripts/fetch_media_v2.py`: Lógica para gerar um prompt de imagem detalhado a partir de um texto.
- `scripts/generate_image.py`: Lógica da chamada para a API Imagen 4, incluindo configuração de aspect ratio e formato.

### Input
- **Lê da tabela `scenes`:**
  - `id` (scene_id)
  - `text_content`
- **Exemplo concreto de input (do job):**
  ```json
  {
    "scene_id": "s1a2b3c4-d5e6-f789-0123-456789abcdef",
    "text_content": "It is said to have housed over 400,000 scrolls, containing the collective wisdom of civilizations from Greece to Persia."
  }
  ```

### Output Esperado
- **Escreve na tabela `scenes`:**
  - `image_prompt`: O prompt detalhado gerado pelo Gemini.
  - `image_url`: A URL da imagem salva no Supabase Storage.
- **Salva no Supabase Storage:**
  - Um arquivo de imagem no bucket `images`.
- **Exemplo concreto de output (no banco e storage):**
  - **scenes:** `image_prompt` = "A vast, ancient library hall with endless shelves of scrolls, sunlight streaming through high windows, scholars of Greek and Persian descent studying manuscripts. Cinematic, photorealistic, 4k.", `image_url` = "https://<project>.supabase.co/storage/v1/object/public/images/a1b2.../s1a2....png"
  - **Storage:** O arquivo `a1b2.../s1a2....png` existe no bucket `images`.

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### Dependências
- **Depende de:** `script_worker`.
- **Dispara:** Nenhum (sinaliza sua conclusão para o `render_worker`).

### Teste Local
```bash
# 1. Configurar env vars
export SUPABASE_URL="..."
export SUPABASE_KEY="..."
export GOOGLE_API_KEY="..."

# 2. Inserir dados de teste (uma cena de uma story existente)
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('scenes').insert({'story_id': '<STORY_ID_EXISTENTE>', 'scene_order': 1, 'text_content': 'A vast ancient library with scrolls.'}).execute(); print(data[1][0]['id'])"

# 3. Rodar o worker
python workers/image_worker.py --scene-id <ID_DA_CENA_ACIMA>

# 4. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('scenes').select('image_url').eq('id', '<ID_DA_CENA_ACIMA>').single().execute(); assert data[1]['image_url'] is not None; print('Success!')"
```

### Critérios de Aceite
- [ ] O campo `image_url` da `scene` deve ser preenchido com uma URL válida do Supabase Storage.
- [ ] A imagem correspondente deve existir no bucket `images` do Storage.
- [ ] O campo `image_prompt` deve ser preenchido.

### Possíveis Erros
- **API do Imagen falha:** Registrar o erro, marcar o job como `failed`. Uma lógica de retry no orquestrador é necessária.
- **Falha no upload para o Storage:** Registrar o erro, marcar o job como `failed`.

---

## Worker: `audio_worker`

### Função
Gera a narração (TTS) para cada cena da história.

### Fase
Fase 2 (Paralelo).

### Script Reutilizado
`scripts/generate_tts.py`
- Lógica de chamada para a API Google Cloud TTS.
- Carregamento de configuração de voz do arquivo `config/voices.yaml`.
- Lógica para dividir textos longos em chunks (se necessário).

### Input
- **Lê da tabela `scenes`:**
  - `id` (scene_id)
  - `text_content`
- **Lê da tabela `stories` (para obter o idioma):**
  - `languages` (o worker usará o primeiro idioma da lista, ex: `en-US` de `['en-US', 'pt-BR']`)
- **Exemplo concreto de input (do job):**
  ```json
  {
    "scene_id": "s1a2b3c4-d5e6-f789-0123-456789abcdef",
    "text_content": "It is said to have housed over 400,000 scrolls...",
    "languages": ["en-US", "pt-BR"]
  }
  ```

### Output Esperado
- **Escreve na tabela `scenes`:**
  - `audio_url`: A URL do áudio salvo no Supabase Storage.
  - `duration_seconds`: A duração do áudio gerado.
- **Salva no Supabase Storage:**
  - Um arquivo de áudio no bucket `audio`.
- **Exemplo concreto de output:**
  - **scenes:** `audio_url` = "https://<project>.supabase.co/storage/v1/object/public/audio/a1b2.../s1a2....mp3", `duration_seconds` = 12.5
  - **Storage:** O arquivo `a1b2.../s1a2....mp3` existe no bucket `audio`.

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### Dependências
- **Depende de:** `script_worker`.
- **Dispara:** Nenhum (sinaliza sua conclusão para o `render_worker`).

### Teste Local
```bash
# 1. Configurar env vars
export SUPABASE_URL="..."
export SUPABASE_KEY="..."
export GOOGLE_API_KEY="..."

# 2. Inserir cena de teste
# (Usar a cena criada no teste do image_worker)

# 3. Rodar o worker
python workers/audio_worker.py --scene-id <ID_DA_CENA_CRIADA>

# 4. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('scenes').select('audio_url, duration_seconds').eq('id', '<ID_DA_CENA_CRIADA>').single().execute(); assert data[1]['audio_url'] is not None and data[1]['duration_seconds'] > 0; print('Success!')"
```

### Critérios de Aceite
- [ ] O campo `audio_url` da `scene` deve ser preenchido com uma URL válida.
- [ ] O áudio correspondente deve existir no bucket `audio` do Storage.
- [ ] O campo `duration_seconds` deve ser preenchido com um valor numérico maior que zero.

### Possíveis Erros
- **API TTS falha:** Registrar o erro e marcar o job como `failed`.
- **Falha no upload para o Storage:** Registrar o erro e marcar o job como `failed`.

---

## Worker: `translation_worker`

### Função
Traduz o texto de cada cena para os idiomas adicionais solicitados.

### Fase
Fase 2 (Paralelo).

### Script Reutilizado
Nenhum script direto, mas a lógica de chamada ao Gemini de `generate_script.py` será adaptada.

### Input
- **Lê da tabela `scenes`:**
  - `id` (scene_id)
  - `text_content`
- **Lê da tabela `stories` (para obter a lista de idiomas):**
  - `languages` (ex: `['en-US', 'pt-BR', 'es-ES']`)
- **Exemplo concreto de input (do job):**
  ```json
  {
    "scene_id": "s1a2b3c4-d5e6-f789-0123-456789abcdef",
    "text_content": "A beacon of human intellect.",
    "languages": ["pt-BR", "es-ES"]
  }
  ```

### Output Esperado
- **Escreve na tabela `scenes`:**
  - `translated_text`: Atualiza o JSONB com as traduções.
- **Exemplo concreto de output:**
  - **scenes:** `translated_text` = `{"pt-BR": "Um farol do intelecto humano.", "es-ES": "Un faro del intelecto humano."}`

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### Dependências
- **Depende de:** `script_worker`.
- **Dispara:** Nenhum.

### Teste Local
```bash
# 1. Configurar env vars
export SUPABASE_URL="..."
export SUPABASE_KEY="..."
export GOOGLE_API_KEY="..."

# 2. Inserir cena de teste e atualizar story com idiomas
# ... (código python para inserir cena e story com languages = ['pt-BR'])

# 3. Rodar o worker
python workers/translation_worker.py --scene-id <ID_DA_CENA>

# 4. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('scenes').select('translated_text').eq('id', '<ID_DA_CENA>').single().execute(); assert 'pt-BR' in data[1]['translated_text']; print('Success!')"
```

### Critérios de Aceite
- [ ] O campo `translated_text` deve conter uma chave para cada idioma solicitado.
- [ ] O valor de cada chave de idioma deve ser uma string não-vazia.

### Possíveis Erros
- **API de tradução falha:** Registrar erro, marcar job como `failed`.

---

## Worker: `render_worker`

### Função
Combina todas as imagens e áudios de uma história para criar o vídeo final.

### Fase
Fase 3 (Gatilho: Pós-Fase 2).

### Script Reutilizado
`scripts/render_video.py`
- Lógica completa do `ffmpeg` para aplicar Ken Burns, concatenar clipes, e mixar áudio.
- Uso do `ffprobe` para obter durações.

### Input
- **Lê da tabela `scenes` (todos de uma `story_id`):**
  - `image_url`
  - `audio_url`
  - `duration_seconds`
- **Exemplo concreto de input (do job):**
  ```json
  {
    "story_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

### Output Esperado
- **Escreve na tabela `stories`:**
  - `video_url`: URL do vídeo final no Storage.
  - `status`: Atualiza para `ready_for_review`.
- **Salva no Supabase Storage:**
  - Um arquivo de vídeo no bucket `videos`.
- **Exemplo concreto de output:**
  - **stories:** `video_url` = "https://<project>.supabase.co/storage/v1/object/public/videos/a1b2....mp4", `status` = 'ready_for_review'
  - **Storage:** O arquivo `a1b2....mp4` existe no bucket `videos`.

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `FFMPEG_PATH` (opcional, se não estiver no PATH do sistema)

### Dependências
- **Depende de:** `image_worker` e `audio_worker` (para todas as cenas).
- **Dispara:** `thumbnail_worker` e `metadata_worker`.

### Teste Local
```bash
# 1. Pré-requisito: Ter uma story com todas as cenas com image_url e audio_url preenchidos.
# ...

# 2. Rodar o worker
python workers/render_worker.py --story-id <STORY_ID_PRONTA>

# 3. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('stories').select('video_url, status').eq('id', '<STORY_ID_PRONTA>').single().execute(); assert data[1]['video_url'] is not None and data[1]['status'] == 'ready_for_review'; print('Success!')"
```

### Critérios de Aceite
- [ ] O campo `video_url` na tabela `stories` deve ser preenchido.
- [ ] O vídeo deve existir no bucket `videos` do Storage.
- [ ] O status da `story` deve ser `ready_for_review`.

### Possíveis Erros
- **`ffmpeg` falha:** Capturar o stderr do `ffmpeg`, registrar no job, e marcar a `story` como `failed`.
- **Arquivos de mídia ausentes:** Se o download de uma imagem ou áudio falhar, o worker deve falhar.

---

## Worker: `thumbnail_worker`

### Função
Gera 3 opções de thumbnail para o vídeo.

### Fase
Fase 3 (Pós-Render).

### Script Reutilizado
- Lógica de `generate_image.py` será usada, mas com um prompt específico para thumbnails.

### Input
- **Lê da tabela `stories`:**
  - `id` (story_id)
  - `topic`
  - `script_text` (para contexto)
- **Exemplo concreto de input (do job):**
  ```json
  {
    "story_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

### Output Esperado
- **Cria na tabela `thumbnail_options`:**
  - 3 novas entradas, cada uma com `story_id` e `image_url`.
- **Salva no Supabase Storage:**
  - 3 arquivos de imagem no bucket `thumbnails`.
- **Exemplo concreto de output:**
  - **thumbnail_options:** 3 registros como `{"story_id": "a1b2...", "image_url": "https://.../thumbnails/a1b2.../thumb1.png"}`
  - **Storage:** 3 imagens no bucket `thumbnails`.

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### Dependências
- **Depende de:** `render_worker`.
- **Dispara:** Nenhum.

### Teste Local
```bash
# 1. Pré-requisito: Ter uma story com status 'ready_for_review'.
# ...

# 2. Rodar o worker
python workers/thumbnail_worker.py --story-id <STORY_ID_PRONTA>

# 3. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('thumbnail_options').select('*').eq('story_id', '<STORY_ID_PRONTA>').execute(); assert len(data[1]) == 3; print('Success!')"
```

### Critérios de Aceite
- [ ] Devem ser criados exatamente 3 registros na tabela `thumbnail_options` para a `story_id`.
- [ ] Cada registro deve ter uma `image_url` válida.
- [ ] As 3 imagens correspondentes devem existir no bucket `thumbnails`.

### Possíveis Erros
- **API do Imagen falha:** Registrar erro e falhar o job. A UI deve permitir um retry manual.

---

## Worker: `metadata_worker`

### Função
Gera 3 opções de título, uma descrição SEO e tags para o vídeo.

### Fase
Fase 3 (Pós-Render).

### Script Reutilizado
`scripts/generate_metadata.py`
- Lógica de prompt para o Gemini, solicitando o JSON estruturado com 3 títulos, descrição e tags.
- Lógica de parse e limpeza da resposta da API.

### Input
- **Lê da tabela `stories`:**
  - `id` (story_id)
  - `topic`
  - `script_text` (para contexto)
- **Exemplo concreto de input (do job):**
  ```json
  {
    "story_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

### Output Esperado
- **Cria na tabela `title_options`:**
  - 3 novas entradas com `story_id` e `title_text`.
- **Escreve na tabela `stories`:**
  - `metadata`: Atualiza o JSONB com a descrição e as tags geradas.
- **Exemplo concreto de output:**
  - **title_options:** 3 registros como `{"story_id": "a1b2...", "title_text": "What If The Library of Alexandria Never Fell?"}`
  - **stories:** `metadata` = `{"description": "...", "tags": ["history", "alexandria", ...]}`

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### Dependências
- **Depende de:** `render_worker`.
- **Dispara:** Nenhum.

### Teste Local
```bash
# 1. Pré-requisito: Ter uma story com status 'ready_for_review'.
# ...

# 2. Rodar o worker
python workers/metadata_worker.py --story-id <STORY_ID_PRONTA>

# 3. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data_titles, count = s.table('title_options').select('*').eq('story_id', '<STORY_ID_PRONTA>').execute(); data_story, count = s.table('stories').select('metadata').eq('id', '<STORY_ID_PRONTA>').single().execute(); assert len(data_titles[1]) == 3; assert 'description' in data_story[1]['metadata']; print('Success!')"
```

### Critérios de Aceite
- [ ] Devem ser criados exatamente 3 registros na tabela `title_options`.
- [ ] O campo `metadata` da `story` deve ser populado com um objeto contendo `description` e `tags`.

### Possíveis Erros
- **API do Gemini falha:** Registrar erro e falhar o job.
- **JSON inválido:** Se a API retornar um formato inesperado, o worker deve falhar com um erro claro.

---

## Worker: `upload_worker`

### Função
Faz o upload do vídeo final e seus metadados para o YouTube.

### Fase
Fase 3 (Gatilho: Ação Humana via API).

### Script Reutilizado
`scripts/upload_youtube.py`
- Lógica de autenticação com a API do YouTube, incluindo refresh de token.
- Função `upload_video` para enviar o arquivo de vídeo e metadados.
- Função `upload_thumbnail` para definir a thumbnail customizada.

### Input
- **Lê da tabela `stories`:**
  - `id` (story_id)
  - `video_url`
  - `selected_title`
  - `selected_thumbnail_url`
  - `metadata` (para descrição e tags)
- **Exemplo concreto de input (do job, disparado pela API):**
  ```json
  {
    "story_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
  }
  ```

### Output Esperado
- **Escreve na tabela `stories`:**
  - `youtube_url` e `youtube_video_id`.
  - `status`: Atualiza para `published`.
- **Exemplo concreto de output:**
  - **stories:** `status` = 'published', `youtube_url` = "https://youtu.be/dQw4w9WgXcQ", `youtube_video_id` = "dQw4w9WgXcQ"

### Variáveis de Ambiente
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `YOUTUBE_TOKEN_JSON` (em base64)

### Dependências
- **Depende de:** Ação humana (chamada na API `POST /stories/{id}/publish`).
- **Dispara:** Nenhum (é o último).

### Teste Local
```bash
# 1. Pré-requisito: Uma story 'ready_for_review' com video_url, título e thumb selecionados.
# ... (código para atualizar a story com selected_title e selected_thumbnail_url)

# 2. Rodar o worker
python workers/upload_worker.py --story-id <STORY_ID_PARA_PUBLICAR>

# 3. Verificar resultado
python -c "from supabase import create_client; s = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY']); data, count = s.table('stories').select('status, youtube_url').eq('id', '<STORY_ID_PARA_PUBLICAR>').single().execute(); assert data[1]['status'] == 'published' and data[1]['youtube_url'] is not None; print('Success!')"
```

### Critérios de Aceite
- [ ] O status da `story` deve ser `published` ao final.
- [ ] Os campos `youtube_url` e `youtube_video_id` devem ser preenchidos.
- [ ] O vídeo deve estar visível no canal do YouTube com o status de privacidade correto.

### Possíveis Erros
- **API do YouTube falha:** Registrar o erro da API, marcar a `story` como `failed`.
- **Token inválido:** O worker deve falhar com uma mensagem clara sobre a necessidade de reautenticação.
- **Falha no download do vídeo/thumb:** Se os arquivos não puderem ser baixados do Storage, o job deve falhar.
