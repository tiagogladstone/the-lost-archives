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
|  PHASE 3: REVIEW & PUBLISH (Human-in-the-loop with Iterative Refinement)   |
|  +------------------+  +--------------------+                             |
|  | thumbnail_worker |  |   metadata_worker  |---> Options written to DB   |
|  +------------------+  +--------------------+                             |
|                                     ^                                     |
|             (Regenerate)            | (Feedback via API)                  |
|                                     +-----------------------+             |
|                                                             |             |
|                 (Human reviews on Dashboard, gives feedback)              |
|  +------------------+                                                       |
|  | User clicks PUBLISH | (when all items approved)                           |
|  +---------+--------+                                                       |
|            | (POST /stories/{id}/publish)                                 |
|            v                                                              |
|  +-----------------+                                                        |
|  |   upload_worker  |-----> Video on YouTube (with 3 titles/thumbs for A/B)|
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

The API is the backbone of the iterative review and publication workflow.

-   ~~`POST /stories/{id}/titles/{title_id}/feedback`~~ **REMOVIDO: Títulos vêm de pesquisa SEO e NÃO são editáveis.**
    -   **Body:** `{"feedback": "troca 'mystery' por 'secret'"}`
    -   **Action:** Triggers an AI regeneration of the specific title using the provided feedback. Updates the `title_text` and increments its `version`. Records the feedback in `feedback_history`.

-   `POST /stories/{id}/titles/{title_id}/approve`
    -   **Action:** Marks a specific title as approved by setting `approved = true`.

-   `POST /stories/{id}/thumbnails/{thumb_id}/feedback`
    -   **Body:** `{"feedback": "aumente o contraste, mude texto para X"}`
    -   **Action:** Triggers an AI regeneration of the thumbnail.

-   `POST /stories/{id}/thumbnails/{thumb_id}/approve`
    -   **Action:** Marks a thumbnail as approved (`approved = true`).

-   `POST /stories/{id}/description/feedback`
    -   **Body:** `{"feedback": "adiciona link do canal no início"}`
    -   **Action:** Regenerates the video description.

-   `POST /stories/{id}/publish`
    -   **Action:** The final step. This endpoint is **only callable if all 3 titles and 3 thumbnails are marked as `approved`**. It triggers the `upload_worker` to send the video and all approved metadata to YouTube for A/B testing.

## 5. Technical Decisions

-   **Human-in-the-Loop:** Introducing a mandatory review step (`ready_for_review` status) prevents fully automated posting, ensuring quality control and adherence to platform guidelines. This is a critical product decision reflected in the architecture.
-   **Parallelization in Phase 2:** Running image, audio, and translation tasks concurrently is the main source of efficiency in the new pipeline, significantly reducing the total time to get a video to the review stage.
-   **Decoupled Publication:** The `upload_worker` is now completely decoupled from the main automated pipeline and is only activated by a direct user action via the API. This is a safer and more deliberate publication model.
-   **State-Driven Orchestration:** The system remains state-driven, with the `status` field in the `stories` table being the source of truth that dictates which phase or action is next.

## 6. Dashboard UX - The Review Page

The `/stories/{id}/review` page is the core of the human-in-the-loop process. It's designed for efficient, iterative feedback.

```
┌─────────────────────────────────────────┐
│ 🎬 Preview do Vídeo                    │
│ [Player com vídeo renderizado]          │
├─────────────────────────────────────────┤
│ 📝 Títulos (3 para teste A/B)          │
│ 1. "The Lost Library..." [✅ Aprovado]  │
│ 2. "Alexandria's Secret" [✏️ Editar]   │
│    └─ Input: "troca Secret por Mystery" │
│    └─ [Regenerar] [Aprovar]             │
│ 3. "What Really Happened" [✅ Aprovado] │
├─────────────────────────────────────────┤
│ 🎨 Thumbnails (3 para teste A/B)       │
│ [Thumb1 ✅] [Thumb2 ✏️] [Thumb3 ✅]    │
│ Thumb2 feedback: "mais contraste"       │
│ [Regenerar] [Aprovar]                   │
├─────────────────────────────────────────┤
│ 📋 Descrição [✅ Aprovada]              │
│ 🏷️ Tags [✅ Aprovadas]                 │
├─────────────────────────────────────────┤
│ [🟢 PUBLICAR NO YOUTUBE]               │
│ (ativo só quando tudo aprovado)         │
└─────────────────────────────────────────┘
```

### User Flow:
1.  **Initial View:** The user sees the rendered video and the first version of all generated assets (titles, thumbnails, description, tags).
2.  **Iterative Feedback:** For any item that isn't perfect, the user can provide text feedback and click "Regenerar". The backend AI workers process this feedback and update the item. The UI reflects the new version.
3.  **Approval:** When an item is satisfactory, the user clicks "Aprovar". The item is marked visually as complete (e.g., with a green checkmark).
4.  **Publication:** The "PUBLICAR NO YOUTUBE" button remains disabled until every single item (all 3 titles, all 3 thumbnails, description, and tags) has been marked as approved. Once clicked, the `publish` action is irreversible.

