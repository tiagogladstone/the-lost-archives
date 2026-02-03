# Plano de Migração: The Lost Archives para SaaS

Este documento detalha o plano de migração do pipeline "The Lost Archives" de uma arquitetura monolítica para um modelo Software-as-a-Service (SaaS) baseado em workers, Supabase e um dashboard no Vercel.

## 1. Pré-requisitos

-   [ ] **Criar projeto no Supabase:**
    -   Acessar [supabase.com](https://supabase.com) e criar um novo projeto no Free Tier.
-   [ ] **Configurar Supabase Storage:**
    -   Dentro do projeto, criar três buckets públicos:
        -   `images`: Para armazenar as imagens geradas para cada cena.
        -   `audio`: Para os arquivos de narração de cada cena.
        -   `videos`: Para os vídeos finais renderizados.
-   [ ] **Obter Credenciais Supabase:**
    -   Navegar até "Project Settings" > "API".
    -   Copiar `SUPABASE_URL` (Project URL) e `SUPABASE_KEY` (o `anon` public key é suficiente para os workers, mas a `service_role` key será necessária para rodar o schema).
-   [ ] **Salvar Credenciais no Vault:**
    -   Armazenar as credenciais de forma segura.
    -   `./scripts/vault.sh set supabase-url "URL_COPIADA"`
    -   `./scripts/vault.sh set supabase-service-key "SERVICE_KEY_COPIADA"`
-   [ ] **Listar Variáveis de Ambiente:**
    -   `SUPABASE_URL`: URL do projeto Supabase.
    -   `SUPABASE_KEY`: Chave de serviço (ou anônima) do Supabase.
    -   `GOOGLE_API_KEY`: Chave de API para Gemini, Imagen e Google TTS.
    -   `YOUTUBE_TOKEN_JSON`: Credenciais de upload para o YouTube (em base64).
    -   `PEXELS_API_KEY`: (Opcional, para fallback) Chave de API do Pexels.

## 2. Configuração do Banco de Dados

-   [ ] **Executar Schema SQL:**
    -   Conectar-se ao banco de dados Supabase e executar o conteúdo do arquivo `database/schema.sql` no SQL Editor para criar as tabelas `stories`, `scenes`, `jobs`, e `assets`.
-   [ ] **Testar Conexão Python:**
    -   Criar um script de teste (`database/supabase_setup.py`) que utiliza as variáveis de ambiente para se conectar ao Supabase e realizar uma query simples (e.g., `select * from stories limit 1`).
-   [ ] **Criar RLS Policies (Opcional):**
    -   Inicialmente, a `service_role` key dará acesso total. Para um ambiente de produção mais seguro, políticas de Row Level Security podem ser adicionadas para restringir o acesso dos workers apenas aos `jobs` que eles podem processar.
-   [ ] **Configurar Realtime:**
    -   No dashboard do Supabase, ir em "Database" > "Replication".
    -   Habilitar a replicação para as tabelas `stories` e `jobs` para que o dashboard Vercel possa receber atualizações em tempo real.

## 3. Implementação dos Workers

A implementação seguirá uma ordem de dependência lógica, começando pela base e avançando pelo pipeline.

### 1. **base_worker.py**
-   **Input:** N/A. É a classe base.
-   **Output:** N/A.
-   **Script Reutilizado:** `workers/base_worker.py`
-   **Modificações:**
    -   Implementar uma lógica de "claim" atômica para jobs, preferencialmente usando uma função RPC no PostgreSQL para evitar race conditions. O `SELECT` seguido de `UPDATE` atual é propenso a falhas sob concorrência.
    -   Adicionar logging mais robusto.
-   **Variáveis de Ambiente:** `SUPABASE_URL`, `SUPABASE_KEY`.
-   **Teste Isolado:** Não pode ser testado diretamente.

### 2. **script_worker.py**
-   **Input:** `job` com `story_id`. O worker busca o `topic` da história no banco.
-   **Output:** Atualiza a tabela `stories` com o `script_text` e cria múltiplas entradas na tabela `scenes`.
-   **Script Reutilizado:** `scripts/generate_script.py` e `workers/script_worker.py`.
-   **Modificações:**
    1.  Integrar a lógica de `generate_script.py` dentro do método `process`.
    2.  Após gerar o script, o worker deve parseá-lo em parágrafos/cenas.
    3.  Para cada cena, inserir uma nova linha na tabela `scenes` com `story_id`, `scene_order` e `text_content`.
    4.  Atualizar o status da `story` para `generating_images`.
    5.  Criar um novo `job` do tipo `generate_images` para a `story`.
-   **Variáveis de Ambiente:** `GOOGLE_API_KEY`.
-   **Teste Isolado:** Chamar o método `process` com um `job` mockado e verificar se as tabelas `stories` e `scenes` são populadas corretamente.

### 3. **image_worker.py**
-   **Input:** `job` com `story_id`. O worker busca todas as `scenes` pendentes para a história.
-   **Output:** Para cada cena, atualiza `image_url` e `image_prompt` na tabela `scenes`.
-   **Script Reutilizado:** `scripts/fetch_media_v2.py` (para a lógica de extração de prompts) e `scripts/generate_image.py`.
-   **Modificações:**
    1.  O worker deve primeiro buscar todas as `scenes` da `story` que não têm `image_url`.
    2.  Para cada cena, usar Gemini para gerar um `image_prompt` a partir do `text_content`.
    3.  Usar a lógica de `generate_image.py` para gerar a imagem.
    4.  Fazer upload da imagem para o bucket `images` no Supabase Storage.
    5.  Atualizar a linha da `scene` com a URL do storage e o prompt usado.
    6.  Quando todas as imagens de uma `story` forem geradas, criar um novo `job` do tipo `generate_audio`.
-   **Variáveis de Ambiente:** `GOOGLE_API_KEY`.
-   **Teste Isolado:** Chamar `process` com um `job` mockado, uma `story` e `scenes` pré-existentes. Verificar se as imagens são criadas no Storage e as URLs atualizadas.

### 4. **audio_worker.py**
-   **Input:** `job` com `story_id`. Busca todas as `scenes` com `image_url` mas sem `audio_url`.
-   **Output:** Para cada cena, atualiza `audio_url` na tabela `scenes`.
-   **Script Reutilizado:** `scripts/generate_tts.py`.
-   **Modificações:**
    1.  Integrar a lógica de `generate_tts.py` para converter o `text_content` de cada cena em áudio.
    2.  Fazer upload do áudio para o bucket `audio` no Supabase Storage.
    3.  Atualizar a `scene` com a `audio_url`.
    4.  Quando todos os áudios de uma `story` forem gerados, criar um `job` do tipo `generate_metadata`.
-   **Variáveis de Ambiente:** `GOOGLE_API_KEY`.
-   **Teste Isolado:** Similar ao `image_worker`.

### 5. **metadata_worker.py**
-   **Input:** `job` com `story_id`. Busca o `script_text` da `story`.
-   **Output:** Atualiza o campo `metadata` (JSONB) na tabela `stories`.
-   **Script Reutilizado:** `scripts/generate_metadata.py`.
-   **Modificações:**
    1.  Integrar a lógica de `generate_metadata.py`.
    2.  Salvar o JSON de metadados diretamente no campo `metadata` da `story`.
    3.  Após a conclusão, criar um `job` do tipo `render_video`.
-   **Variáveis de Ambiente:** `GOOGLE_API_KEY`.
-   **Teste Isolado:** Chamar com `job` mockado e verificar se o JSON na tabela `stories` é atualizado corretamente.

### 6. **render_worker.py**
-   **Input:** `job` com `story_id`.
-   **Output:** Cria o vídeo final e o armazena no bucket `videos` do Supabase Storage.
-   **Script Reutilizado:** `scripts/render_video.py` e `scripts/apply_ken_burns.py`.
-   **Modificações:**
    1.  O worker precisa baixar todas as `images` e `audios` da `story` a partir das URLs no Supabase Storage para um diretório temporário.
    2.  Concatenar os áudios das cenas em um único arquivo de narração.
    3.  Executar a lógica de `render_video.py`, que já inclui o efeito Ken Burns.
    4.  Fazer upload do vídeo final para o bucket `videos`.
    5.  Criar um `job` do tipo `upload_youtube`.
-   **Variáveis de Ambiente:** N/A (requer FFmpeg instalado no ambiente de execução).
-   **Teste Isolado:** O mais complexo. Requer `story`, `scenes` com `image_url` e `audio_url` populadas. Verificar se o vídeo é gerado e enviado ao Storage.

### 7. **upload_worker.py**
-   **Input:** `job` com `story_id`. Busca o vídeo final do Storage e os metadados da `story`.
-   **Output:** Atualiza `youtube_url` e `youtube_video_id` na `story` e muda seu status para `published`.
-   **Script Reutilizado:** `scripts/upload_youtube.py`.
-   **Modificações:**
    1.  Baixar o vídeo final do bucket `videos`.
    2.  Extrair `title`, `description` e `tags` do campo `metadata` da `story`.
    3.  Executar a lógica de `upload_youtube.py`.
    4.  Atualizar a `story` com o link do YouTube e o status final.
-   **Variáveis de Ambiente:** `YOUTUBE_TOKEN_JSON`.
-   **Teste Isolado:** Requer um vídeo de teste no Storage e metadados na `story`. Verificar se o vídeo é enviado ao YouTube e a `story` é atualizada.

## 4. Orquestrador

-   **Disparo Inicial:** A criação de uma nova `story` via API (ver Seção 5) deve automaticamente criar o primeiro `job` na fila, do tipo `generate_script`.
-   **Encadeamento:** Cada worker, ao concluir sua tarefa para uma `story`, é responsável por criar o `job` da etapa seguinte. Isso cria uma cadeia de eventos descentralizada e resiliente.
    -   `script_worker` (fim) → cria `job(generate_images)`
    -   `image_worker` (fim, todas as imagens prontas) → cria `job(generate_audio)`
    -   `audio_worker` (fim, todos os áudios prontos) → cria `job(generate_metadata)`
    -   `metadata_worker` (fim) → cria `job(render_video)`
    -   `render_worker` (fim) → cria `job(upload_youtube)`
    -   `upload_worker` (fim) → finaliza o processo.

## 5. API (FastAPI)

Uma API simples em FastAPI será o ponto de entrada para o sistema.

-   `POST /stories`:
    -   **Body:** `{ "topic": "string", "language": "string" }`
    -   **Ação:** Cria uma nova `story` na tabela com status `pending`. Cria o primeiro `job` (`generate_script`) para essa `story`.
    -   **Retorno:** `{ "story_id": "uuid" }`
-   `GET /stories`:
    -   **Ação:** Lista todas as `stories`, com status e timestamps.
    -   **Retorno:** `[ { "id": ..., "topic": ..., "status": ... } ]`
-   `GET /stories/{id}`:
    -   **Ação:** Retorna os detalhes de uma `story`, incluindo suas `scenes`.
    -   **Retorno:** `{ "id": ..., "status": ..., "scenes": [ ... ] }`
-   `POST /stories/{id}/retry`:
    -   **Ação:** Se uma `story` falhou (`status: 'failed'`), permite reenfileirar o último `job` que falhou.
-   `DELETE /stories/{id}`:
    -   **Ação:** Cancela uma `story` em andamento e seus `jobs` associados.

## 6. Dashboard Vercel

-   **Stack:** Next.js 14, TypeScript, Supabase-JS, Tailwind CSS.
-   **Páginas:**
    -   `/` (Dashboard): Lista de todas as `stories` em uma tabela. Colunas: Tópico, Status, Criado em, Link do YouTube. O status deve ser atualizado em tempo real usando o Supabase Realtime.
    -   `/new` (Criar Vídeo): Um formulário simples com campos "Tópico" e "Idioma" que faz um POST para a API `/stories`.
    -   `/stories/{id}` (Detalhes): Mostra o progresso detalhado de uma `story`, listando cada `scene` e seu status individual (imagem, áudio).
-   **Autenticação:** Supabase Auth pode ser usado para proteger o dashboard.
-   **Deploy:** Configurado com a integração Vercel + GitHub para deploy contínuo.

## 7. Deploy

-   **Workers:** Cada worker será empacotado em sua própria imagem Docker e deployado como um serviço separado no Cloud Run. Isso permite escalar cada parte do pipeline de forma independente.
-   **API:** O servidor FastAPI também será deployado como um serviço Cloud Run.
-   **Variáveis de Ambiente:** As credenciais e configurações serão injetadas em cada serviço do Cloud Run através de Secret Manager ou variáveis de ambiente diretas.
-   **CI/CD:** Um workflow simples no GitHub Actions pode ser configurado para construir e deployar as imagens Docker no Cloud Run a cada push para a branch `main`.

## 8. Transição

-   **Fase 1 (Desenvolvimento):** Manter o monolito (`main.py`) operacional para produção. Desenvolver e testar os workers e a API em um ambiente de staging separado.
-   **Fase 2 (Teste E2E):** Após testes isolados, realizar testes de ponta a ponta, criando histórias pela API e garantindo que o vídeo final seja gerado e enviado corretamente.
-   **Fase 3 (Cutover):** Uma vez que a nova arquitetura SaaS esteja estável e validada, o endpoint do Cloud Run do monolito pode ser desativado. A transição é "big bang", já que não há estado de usuário a ser migrado, apenas o processo de backend.

## 9. Custos Estimados (Por Vídeo)

-   **Supabase:** Free Tier (500MB DB, 1GB storage) deve ser suficiente para os primeiros ~100 vídeos. Custo marginal baixo depois disso.
-   **Cloud Run:** Dentro do free tier generoso do Google Cloud, ou custo mínimo por execução.
-   **Vercel:** Free tier para o dashboard.
-   **APIs (Custo Principal):**
    -   **Gemini (Script/Metadata/Prompts):** ~20.000 tokens por vídeo. Custo ~$0.02.
    -   **Imagen 4 (Imagens):** ~15 imagens por vídeo @ $0.02/imagem = $0.30.
    -   **Google TTS (Áudio):** ~10.000 caracteres por vídeo. Custo ~$0.02.
-   **Custo Total Estimado por Vídeo:** **~$0.34** (sem incluir custos de fallback ou processamento).

## 10. Checklist de Implementação

| Tarefa                                        | Quem           | Estimativa | Status      |
| --------------------------------------------- | -------------- | ---------- | ----------- |
| **Setup (Seção 1 & 2)**                       |                | **2h**     |             |
| Criar projeto e buckets Supabase              | Manual         | 30 min     | `[ ] ToDo`  |
| Salvar credenciais no vault                    | Manual         | 15 min     | `[ ] ToDo`  |
| Rodar schema e testar conexão                 | Subagente      | 1h 15min   | `[ ] ToDo`  |
| **Workers (Seção 3)**                         |                | **1-2 Dias** |             |
| Implementar `script_worker.py`                | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `image_worker.py`                 | Subagente      | 3h         | `[ ] ToDo`  |
| Implementar `audio_worker.py`                 | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `metadata_worker.py`              | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `render_worker.py`                | Subagente      | 4h         | `[ ] ToDo`  |
| Implementar `upload_worker.py`                | Subagente      | 2h         | `[ ] ToDo`  |
| **API & Dashboard (Seção 5 & 6)**             |                | **1-2 Dias** |             |
| Desenvolver API FastAPI                       | Subagente      | 4h         | `[ ] ToDo`  |
| Criar esqueleto do Dashboard Next.js          | Subagente      | 3h         | `[ ] ToDo`  |
| Implementar páginas e Realtime                | Subagente      | 5h         | `[ ] ToDo`  |
| **Deploy & Testes (Seção 7 & 8)**             |                | **1 Dia**    |             |
| Criar Dockerfiles para workers e API          | Subagente      | 3h         | `[ ] ToDo`  |
| Configurar Cloud Run services                 | Manual         | 2h         | `[ ] ToDo`  |
| Realizar teste de ponta a ponta (E2E)         | Manual         | 3h         | `[ ] ToDo`  |
| **Finalização**                               |                | **30 min**   |             |
| Desativar monolito antigo                     | Manual         | 15 min     | `[ ] ToDo`  |
| Revisar documentação final                    | Subagente      | 15 min     | `[ ] ToDo`  |
