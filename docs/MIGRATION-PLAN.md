## 1. Visão Geral e Novo Fluxo

Este documento detalha o plano de migração do pipeline "The Lost Archives" de uma arquitetura monolítica para um modelo Software-as-a-Service (SaaS) refinado. A mudança principal é a transição de um fluxo sequencial de 7 workers para um **fluxo de 3 fases** com processamento paralelo e um passo de **revisão humana obrigatória** antes da publicação.

### Status Flow
O status de uma `story` seguirá o seguinte fluxo:
`pending` → `generating_script` → `producing` → `rendering` → `ready_for_review` → `publishing` → `published`

Em caso de erro, o status mudará para `failed`, com uma `error_message` e a possibilidade de `retry`.

### Input do Sistema
A criação de uma nova história (story) agora requer os seguintes campos:
-   **Tema** (obrigatório): O tópico central do vídeo (ex: "The Library of Alexandria").
-   **Descrição breve** (obrigatório): 2-3 frases de contexto sobre o tema.
-   **Duração estimada** (obrigatório): Em minutos (ex: 8).
-   **Idiomas** (opcional, default: `en-US`): Lista de idiomas para tradução (ex: `['pt-BR', 'es-ES']`).

## 2. Pré-requisitos

-   [ ] **Criar projeto no Supabase:**
    -   Acessar [supabase.com](https://supabase.com) e criar um novo projeto no Free Tier.
-   [ ] **Configurar Supabase Storage:**
    -   Dentro do projeto, criar os seguintes buckets públicos:
        -   `images`: Para armazenar as imagens geradas para cada cena.
        -   `audio`: Para os arquivos de narração de cada cena.
        -   `videos`: Para os vídeos finais renderizados.
        -   `thumbnails`: Para as opções de thumbnail geradas.
-   [ ] **Obter Credenciais Supabase:**
    -   Navegar até "Project Settings" > "API".
    -   Copiar `SUPABASE_URL` e `SUPABASE_KEY` (`service_role`).
-   [ ] **Salvar Credenciais no Vault:**
    -   `./scripts/vault.sh set supabase-url "URL_COPIADA"`
    -   `./scripts/vault.sh set supabase-service-key "SERVICE_KEY_COPIADA"`
-   [ ] **Listar Variáveis de Ambiente:**
    -   `SUPABASE_URL`, `SUPABASE_KEY`
    -   `GOOGLE_API_KEY` (Gemini, Imagen, Google TTS)
    -   `YOUTUBE_TOKEN_JSON` (em base64)

## 3. Configuração do Banco de Dados

-   [ ] **Executar Schema SQL:**
    -   Conectar-se ao banco de dados Supabase e executar o conteúdo atualizado do arquivo `database/schema.sql`. Isso criará as tabelas `stories`, `scenes`, `title_options`, e `thumbnail_options`.
-   [ ] **Testar Conexão Python:**
    -   Garantir que um script de teste (`database/supabase_setup.py`) consegue se conectar e fazer queries nas novas tabelas.
-   [ ] **Configurar Realtime:**
    -   Habilitar a replicação para as tabelas `stories`, `title_options`, e `thumbnail_options` para que o dashboard Vercel receba atualizações em tempo real.

## 4. O Fluxo de 3 Fases

A arquitetura é baseada em três fases distintas que orquestram a criação do vídeo.

### **FASE 1 - Roteiro (Sequencial)**

Nesta fase, apenas um worker é executado para criar a base da história.

-   **Worker:** `script_worker`
-   **Input:** Tema, descrição e duração.
-   **Ação:**
    1.  Usa Gemini para gerar um roteiro completo.
    2.  Divide o roteiro em `scenes` (parágrafos).
    3.  Popula a tabela `scenes` com o texto de cada cena.
-   **Output:** Roteiro completo dividido em cenas.
-   **Transição:** Ao concluir, o status da `story` muda de `generating_script` para `producing`.

### **FASE 2 - Produção (Paralelo)**

Quando o roteiro está pronto, múltiplos workers são disparados para rodar em paralelo, cada um cuidando de um aspecto da produção.

-   **Worker:** `image_worker`
    -   **Ação:** Gera de 10 a 15 imagens (uma por cena) usando Imagen 4.
    -   **Output:** Salva as imagens no Supabase Storage e atualiza as `scenes` com as `image_url`.
-   **Worker:** `audio_worker`
    -   **Ação:** Gera a narração TTS para o texto de cada cena.
    -   **Output:** Salva os arquivos de áudio no Supabase Storage e atualiza as `scenes` com as `audio_url`.
-   **Worker:** `translation_worker` (NOVO!)
    -   **Ação:** Traduz o roteiro de cada cena para os idiomas solicitados (ex: PT-BR, ES-ES).
    -   **Output:** Atualiza o campo `translated_text` (JSONB) em cada `scene`.

### **FASE 3 - Pós-Produção e Revisão (Sequencial com Gatilho Humano)**

Esta fase começa quando as tarefas da Fase 2 são concluídas e culmina na publicação, que só ocorre após aprovação manual.

1.  **Renderização**
    -   **Worker:** `render_worker`
    -   **Gatilho:** Inicia quando todas as imagens e áudios da Fase 2 estão prontos.
    -   **Ação:**
        1.  Baixa todas as imagens e áudios.
        2.  Aplica o efeito Ken Burns nas imagens.
        3.  Usa FFmpeg para combinar imagem e áudio, criando o vídeo final.
    -   **Output:** Vídeo final salvo no Supabase Storage.
    -   **Transição:** Ao concluir, o status da `story` muda de `rendering` para `ready_for_review`.

2.  **Preparação para Revisão**
    -   **Worker:** `thumbnail_worker` (NOVO!)
        -   **Ação:** Gera 3 opções de thumbnail para o vídeo.
        -   **Output:** Salva as thumbnails no Storage e cria 3 entradas na tabela `thumbnail_options`.
    -   **Worker:** `metadata_worker`
        -   **Ação:** Gera 3 opções de título, uma descrição otimizada para SEO e tags relevantes.
        -   **Output:** Cria 3 entradas na tabela `title_options` e atualiza a `story` com a descrição e tags.

3.  **Revisão Humana (Dashboard)**
    -   O sistema agora **PARA** e aguarda a intervenção humana.
    -   No Dashboard, na página `/stories/{id}/review`, o usuário vê o vídeo renderizado, junto com as 3 opções de título e 3 opções de thumbnail.
    -   **Fluxo de Review no Dashboard:**
        1.  Sistema gera 3 thumbnails + 3 títulos + descrição + tags.
        2.  Usuário vê preview de TUDO no dashboard.
        3.  O usuário deve **SELECIONAR** o melhor título e a melhor thumbnail entre as opções geradas.
        4.  Opcionalmente, o usuário pode editar a descrição e as tags.
        5.  Após a seleção de 1 título e 1 thumbnail, o botão "PUBLICAR" fica ativo.
    -   **Importante:** A pesquisa indicou que a API do YouTube não suporta o upload de múltiplas thumbnails/títulos para um teste A/B nativo no momento do upload. A funcionalidade "Testar e comparar" do YouTube é configurada no YouTube Studio após o upload. Portanto, o fluxo foi corrigido para "selecionar 1 de 3".
    -   A `story` permanece no estado `ready_for_review` até que o botão "PUBLICAR" seja clicado.

4.  **Publicação**
    -   **Worker:** `upload_worker`
    -   **Gatilho:** Disparado pela chamada da API `POST /stories/{id}/publish`.
    -   **Ação:**
        1.  Baixa o vídeo final.
        2.  Usa o título e thumbnail selecionados pelo usuário.
        3.  Faz o upload do vídeo para o YouTube.
    -   **Output:** Atualiza a `story` com a `youtube_url`.
    -   **Transição:** O status final muda para `published`.

## 5. API (FastAPI)

A API é o ponto de entrada e o mecanismo de controle para o fluxo de revisão.

-   `POST /stories`:
    -   **Body:** `{ "topic": "string", "description": "string", "target_duration_minutes": integer, "languages": ["string"] }`
    -   **Ação:** Cria uma nova `story` e inicia a Fase 1.
-   `GET /stories`:
    -   **Ação:** Lista todas as `stories` e seus status.
-   `GET /stories/{id}`:
    -   **Ação:** Retorna os detalhes de uma `story`.
-   `GET /stories/{id}/review`:
    -   **Ação:** Retorna todos os dados necessários para a página de revisão: preview do vídeo, opções de título e opções de thumbnail.
-   `POST /stories/{id}/select-title`:
    -   **Body:** `{ "title_option_id": "uuid" }`
    -   **Ação:** Marca um título como `selected_title` na tabela `stories`.
-   `POST /stories/{id}/select-thumbnail`:
    -   **Body:** `{ "thumbnail_option_id": "uuid" }`
    -   **Ação:** Marca a URL de uma thumbnail como `selected_thumbnail_url` na tabela `stories`.
-   `POST /stories/{id}/publish`:
    -   **Ação:** Dispara o `upload_worker` para publicar o vídeo com os metadados selecionados. Requer que `selected_title` e `selected_thumbnail_url` não estejam nulos.
-   `POST /stories/{id}/retry`:
    -   **Ação:** Re-enfileira o último job que falhou para a `story`.

## 6. Dashboard Vercel

-   **Stack:** Next.js 14, TypeScript, Supabase-JS, Tailwind CSS.
-   **Páginas:**
    -   `/` (Dashboard): Lista de `stories` com status em tempo real.
    -   `/new` (Criar Vídeo): Formulário com os novos campos de input.
    -   `/stories/{id}` (Detalhes): Progresso detalhado de uma `story`.
    -   **`/stories/{id}/review` (NOVO!)**: Página de revisão onde o usuário assiste ao preview, seleciona título e thumbnail, edita metadados e clica em "Publicar".

## 7. Deploy

-   **Workers:** Cada worker será empacotado em sua própria imagem Docker e deployado como um serviço separado no Cloud Run.
-   **API:** O servidor FastAPI também será deployado como um serviço Cloud Run.
-   **CI/CD:** GitHub Actions para construir e deployar as imagens Docker no Cloud Run a cada push para a `main`.
-   **Autenticação:** A API será protegida por uma API Key no header `X-API-Key`. A configuração será gerenciada via Secret Manager no Google Cloud.

## 8. Transição

-   A transição continua sendo "big bang", com a nova arquitetura substituindo o monolito após testes E2E completos.

## 9. Custos Estimados (Por Vídeo)

-   **Supabase:** Free Tier para os primeiros ~100 vídeos.
-   **Cloud Run:** Custo mínimo por execução.
-   **Vercel:** Free tier.
-   **APIs (Custo Principal):**
    -   **Gemini (Script/Metadata/Prompts/Translation):** ~30.000 tokens por vídeo (incluindo tradução). Custo ~$0.03.
    -   **Imagen 4 (Imagens):** ~15 imagens @ $0.02/imagem = $0.30.
    -   **Google TTS (Áudio):** ~10.000 caracteres. Custo ~$0.02.
-   **Custo Total Estimado por Vídeo:** **~$0.35**

## 10. Checklist de Implementação

| Tarefa                                        | Quem           | Estimativa | Status      |
| --------------------------------------------- | -------------- | ---------- | ----------- |
| **Setup (Seção 2 & 3)**                       |                | **2h**     |             |
| Criar projeto e buckets Supabase              | Manual         | 30 min     | `[ ] ToDo`  |
| Salvar credenciais no vault                    | Manual         | 15 min     | `[ ] ToDo`  |
| Rodar schema e testar conexão                 | Subagente      | 1h 15min   | `[ ] ToDo`  |
| **Workers (Seção 4)**                         |                | **2-3 Dias** |             |
| Implementar `script_worker.py`                | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `image_worker.py` (paralelo)      | Subagente      | 3h         | `[ ] ToDo`  |
| Implementar `audio_worker.py` (paralelo)      | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `translation_worker.py` (paralelo)| Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `render_worker.py`                | Subagente      | 4h         | `[ ] ToDo`  |
| Implementar `thumbnail_worker.py`             | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `metadata_worker.py` (com opções) | Subagente      | 2h         | `[ ] ToDo`  |
| Implementar `upload_worker.py`                | Subagente      | 2h         | `[ ] ToDo`  |
| **API & Dashboard (Seção 5 & 6)**             |                | **2 Dias**   |             |
| Desenvolver API FastAPI (com novos endpoints) | Subagente      | 5h         | `[ ] ToDo`  |
| Criar esqueleto do Dashboard Next.js          | Subagente      | 3h         | `[ ] ToDo`  |
| Implementar página de Revisão                 | Subagente      | 6h         | `[ ] ToDo`  |
| **Deploy & Testes (Seção 7 & 8)**             |                | **1 Dia**    |             |
| Criar Dockerfiles para workers e API          | Subagente      | 3h         | `[ ] ToDo`  |
| Configurar Cloud Run services                 | Manual         | 2h         | `[ ] ToDo`  |
| Realizar teste de ponta a ponta (E2E)         | Manual         | 3h         | `[ ] ToDo`  |
| **Finalização**                               |                | **30 min**   |             |
| Desativar monolito antigo                     | Manual         | 15 min     | `[ ] ToDo`  |
| Revisar documentação final                    | Subagente      | 15 min     | `[ ] ToDo`  |