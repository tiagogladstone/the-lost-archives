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
|                                                                           |
|                 (Human reviews on Dashboard)                              |
|  +------------------+                                                       |
|  | User clicks PUBLISH |                                                     |
|  +---------+--------+                                                       |
|            | (POST /stories/{id}/publish)                                 |
|            v                                                              |
|  +-----------------+                                                        |
|  |   upload_worker  |-----> Video on YouTube                               |
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

The API is now more integral to the workflow, especially for the review process.

-   `POST /stories`
    -   **Body:** `{ "topic", "description", "target_duration_minutes", "languages" }`
    -   **Action:** Creates a new story, kicking off Phase 1.
-   `GET /stories/{id}/review`
    -   **Action:** Gathers all necessary data for the review page: the video URL from storage, the three title options, and the three thumbnail options.
-   `POST /stories/{id}/select-title`
    -   **Action:** Updates the database to mark a specific title option as selected.
-   `POST /stories/{id}/select-thumbnail`
    -   **Action:** Updates the database to mark a thumbnail as selected.
-   `POST /stories/{id}/publish`
    -   **Action:** The final user approval. This is the sole trigger for the `upload_worker`.

## 5. Technical Decisions

-   **Human-in-the-Loop:** Introducing a mandatory review step (`ready_for_review` status) prevents fully automated posting, ensuring quality control and adherence to platform guidelines. This is a critical product decision reflected in the architecture.
-   **Parallelization in Phase 2:** Running image, audio, and translation tasks concurrently is the main source of efficiency in the new pipeline, significantly reducing the total time to get a video to the review stage.
-   **Decoupled Publication:** The `upload_worker` is now completely decoupled from the main automated pipeline and is only activated by a direct user action via the API. This is a safer and more deliberate publication model.
-   **State-Driven Orchestration:** The system remains state-driven, with the `status` field in the `stories` table being the source of truth that dictates which phase or action is next.
