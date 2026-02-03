# Architecture: The Lost Archives - Refined SaaS Pipeline

This document outlines the refined SaaS architecture for the "The Lost Archives" YouTube channel. The system is designed around a **3-phase flow** featuring parallel processing and a mandatory human review step, orchestrated via a Supabase backend.

## 1. High-Level Architecture Diagram

```
+-------------------+      +----------------------+      +-----------------+
| Vercel Dashboard  |----->| API (FastAPI)        |----->|   Supabase DB   |
| (Human Interface) |      | (Cloud Run)          |      |   (PostgreSQL   |
+---------+---------+      +----------------------+      |    + Storage)   |
          |                                              +--------+--------+
          |                                                       |
          | (POST /stories)                                       | (triggers...)
          |                                                       v
+---------v-------------------------------------------------------+---------+
|                                                                           |
|  PHASE 1: SCRIPT (Sequential)                                             |
|  +-----------------+       +----------------+                             |
|  |   script_worker |------>| scenes created |                             |
|  +-----------------+       +----------------+                             |
|                                                                           |
+---------------------------------+-------------------+---------------------+
                                  | (status: 'producing')
                                  v
+---------------------------------+-----------------------------------------+
|                                                                           |
|  PHASE 2: PRODUCTION (Parallel)                                           |
|  +-----------------+  +------------------+  +-----------------------+     |
|  |   image_worker  |  |   audio_worker   |  |   translation_worker  |     |
|  +-----------------+  +------------------+  +-----------------------+     |
|          |                  |                       |                       |
|          +------------------+-----------------------+                       |
|                             v                                               |
|               (all assets ready)                                          |
|                             v                                               |
|  +-----------------+                                                        |
|  |  render_worker  |-----> Video Rendered to Storage                       |
|  +-----------------+                                                        |
|                                                                           |
+---------------------------------+-------------------+---------------------+
                                  | (status: 'ready_for_review')
                                  v
+---------------------------------+-----------------------------------------+
|                                                                           |
|  PHASE 3: REVIEW & PUBLISH (Human-in-the-loop)                            |
|  +------------------+  +--------------------+                             |
|  | thumbnail_worker |  |   metadata_worker  |---> Options written to DB   |
|  +------------------+  +--------------------+                             |
|                                     ^                                     |
|                                     | (API Call)                          |
|                                     +-----------------------+             |
|                                                             |             |
|                 (Human reviews and selects 1 title/thumb on Dashboard)    |
|  +------------------+                                                       |
|  | User clicks PUBLISH | (when 1 title/thumb are selected)                   |
|  +---------+--------+                                                       |
|            | (POST /stories/{id}/publish)                                 |
|            v                                                              |
|  +-----------------+                                                        |
|  |   upload_worker  |-----> Video on YouTube (with selected title/thumb)   |
|  +-----------------+                                                        |
|                                                                           |
+---------------------------------------------------------------------------+

```

## 2. Worker & Phase Descriptions

### Phase 1: Roteiro (Scripting)
A single, sequential step to generate the narrative foundation.

-   **`script_worker`**:
    -   **Trigger:** A new `story` is created via the API.
    -   **Action:** Takes the story's `topic`, `description`, and `target_duration_minutes` to generate a full script using Gemini. It then parses this script into individual `scenes`.
    -   **Output:** Creates multiple rows in the `scenes` table, linked to the parent `story`.

### Phase 2: Produção (Production)
A set of parallel workers that create the raw assets for the video.

-   **`image_worker`**:
    -   **Action:** For each scene, generates a corresponding image using Imagen 4.
    -   **Output:** Uploads the image to Supabase Storage and updates the `image_url` for the scene.
-   **`audio_worker`**:
    -   **Action:** For each scene, converts the `text_content` to speech.
    -   **Output:** Uploads the audio to Supabase Storage and updates the `audio_url` for the scene.
-   **`translation_worker`**:
    -   **Action:** Translates the `text_content` of each scene into the languages specified in the story creation.
    -   **Output:** Updates the `translated_text` JSONB field for the scene.
-   **`render_worker`**:
    -   **Trigger:** Runs only after the `image_worker` and `audio_worker` have completed for all scenes of a story.
    -   **Action:** Downloads all images and audio files, applies Ken Burns effect to images, and uses FFmpeg to compile them into the final video.
    -   **Output:** The final `video.mp4` is uploaded to Supabase Storage.

### Phase 3: Revisão e Publicação (Review & Publish)
This phase prepares the metadata and waits for a human decision before going live.

-   **`thumbnail_worker`**:
    -   **Trigger:** Runs after the `render_worker` is complete.
    -   **Action:** Generates 3 distinct thumbnail options for the video.
    -   **Output:** Uploads thumbnails to Storage and creates entries in the `thumbnail_options` table.
-   **`metadata_worker`**:
    -   **Trigger:** Runs after the `render_worker` is complete.
    -   **Action:** Generates 3 title options, an SEO-optimized description, and relevant tags.
    -   **Output:** Creates entries in the `title_options` table and updates the `story`'s metadata.
-   **`upload_worker`**:
    -   **Trigger:** **STRICTLY** triggered by an API call from the dashboard (`POST /stories/{id}/publish`). It does not run automatically.
    -   **Action:** Fetches the final video, the user-selected title and thumbnail, and uploads everything to YouTube.
    -   **Output:** Updates the `story` with the `youtube_url`.

## 3. State Flows

### Story Status Flow
The primary state machine for a video's lifecycle, reflecting the new phases.

`pending` → `generating_script` → `producing` → `rendering` → `ready_for_review` → `publishing` → `published`

-   A `failed` status can occur at any stage, logging an `error_message`.

### Job Status Flow
Each task processed by a worker follows this simple lifecycle.

`queued` → `processing` → `completed` | `failed`

## 4. API Endpoints

The API is the backbone of the review and publication workflow.

-   `POST /stories/{id}/select-title`:
    -   **Body:** `{"title_option_id": "uuid"}`
    -   **Action:** Associates the selected title with the parent story.

-   `POST /stories/{id}/select-thumbnail`:
    -   **Body:** `{"thumbnail_option_id": "uuid"}`
    -   **Action:** Associates the selected thumbnail with the parent story.

-   `POST /stories/{id}/publish`:
    -   **Action:** The final step. This endpoint is **only callable if a title and thumbnail have been selected**. It triggers the `upload_worker` to send the video and selected metadata to YouTube.

## 5. Technical Decisions

-   **Human-in-the-Loop:** Introducing a mandatory review step (`ready_for_review` status) prevents fully automated posting, ensuring quality control. The user must select one title and one thumbnail before publishing.
-   **Correction on YouTube A/B Testing:** Initial documentation assumed the YouTube API supported uploading multiple titles/thumbnails for A/B testing. Research during the audit correction phase indicated this is **not the case**. The "Test & Compare" feature is a YouTube Studio tool used *after* upload. The architecture has been corrected to a "select 1 of 3" model.
-   **Parallelization in Phase 2:** Running image, audio, and translation tasks concurrently is the main source of efficiency in the new pipeline.
-   **Decoupled Publication:** The `upload_worker` is now completely decoupled from the main automated pipeline and is only activated by a direct user action via the API.
-   **State-Driven Orchestration:** The system remains state-driven, with the `status` field in the `stories` table being the source of truth that dictates which phase or action is next.

## 6. Dashboard UX - The Review Page

The `/stories/{id}/review` page is the core of the human-in-the-loop process.

```
┌─────────────────────────────────────────┐
│ 🎬 Preview do Vídeo                    │
│ [Player com vídeo renderizado]          │
├─────────────────────────────────────────┤
│ 📝 Títulos (Selecione 1)               │
│ 🔘 "The Lost Library..."               │
│ 🔘 "Alexandria's Secret" [SELECTED]     │
│ 🔘 "What Really Happened"               │
├─────────────────────────────────────────┤
│ 🎨 Thumbnails (Selecione 1)            │
│ [Thumb1] [Thumb2 SELECTED] [Thumb3]     │
├─────────────────────────────────────────┤
│ 📋 Descrição [Editável]                 │
│ 🏷️ Tags [Editável]                     │
├─────────────────────────────────────────┤
│ [🟢 PUBLICAR NO YOUTUBE]               │
│ (ativo só quando 1 de cada selecionado) │
└─────────────────────────────────────────┘
```

### User Flow:
1.  **Initial View:** The user sees the rendered video and the 3 options for title and thumbnail.
2.  **Selection:** The user must select one title and one thumbnail.
3.  **Publication:** The "PUBLICAR NO YOUTUBE" button becomes active only after a title and a thumbnail have been selected. Once clicked, the `publish` action is irreversible.

## 7. Orquestração Descentralizada

Para resolver o bloqueio identificado na auditoria sobre a falta de um "cérebro" orquestrador, o sistema adota um modelo de orquestração descentralizada. Em vez de um serviço central monitorando o estado, cada worker, ao concluir sua tarefa com sucesso, é responsável por verificar se o seu trabalho desbloqueia a próxima fase do pipeline.

### Lógica de Avanço (Check and Advance)
A lógica é implementada no `base_worker.py` através do método `check_and_advance(story_id)`.

- **`script_worker` termina:** Cria 3 jobs em paralelo: `generate_images`, `generate_audio`, `generate_translations`. (Esta lógica específica é implementada no `script_worker` em si, não na função base).

- **`image_worker` ou `audio_worker` terminam:**
    - Ao final de seu job, o worker chama `check_and_advance`.
    - Esta função verifica se **TODAS** as cenas da história já têm tanto `image_url` quanto `audio_url`.
    - Se a condição for atendida (ou seja, este worker foi o último dos dois tipos a terminar), ele cria o job `render_video` e atualiza o status da história para `rendering`.
    - Se a condição não for atendida, ele não faz nada, pois o outro worker ainda está em andamento e fará a verificação quando terminar.

- **`render_worker` termina:**
    - Chama `check_and_advance`.
    - A função verifica se o status é `rendering` e se a `video_url` existe.
    - Se sim, cria os jobs `generate_thumbnails` e `generate_metadata` em paralelo.

- **`thumbnail_worker` ou `metadata_worker` terminam:**
    - Chama `check_and_advance`.
    - A função verifica se os resultados de ambos os workers já existem no banco de dados.
    - Se sim, o último worker a terminar atualiza o status da história para `ready_for_review`.

- **`upload_worker`:**
    - Não participa da orquestração automática. É disparado unicamente por uma ação humana através de uma chamada de API.

Este modelo remove a necessidade de um serviço orquestrador separado, tornando a arquitetura mais resiliente e simples. A lógica de transição de estado é distribuída entre os próprios workers que executam as tarefas.
