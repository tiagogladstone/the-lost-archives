# Architecture: The Lost Archives - SaaS Pipeline

This document outlines the SaaS architecture for the automated YouTube channel "The Lost Archives". The system is designed as a distributed set of workers that communicate via a central database, which acts as a job queue.

## 1. Architecture Diagram (ASCII)

```
              +-----------------+      +-----------------+      +-----------------+
              |   API Gateway   |----->|  New Story API  |----->|   Supabase DB   |
              | (e.g., Cloud Run) |      |  (FastAPI)      |      | (PostgreSQL)    |
              +-----------------+      +-------+---------+      +--------+--------+
                                               |                           ^
                                               |                           | (Update Status)
                                               v                           |
                                       +-------+---------+      +----------+----------+
                                       |      JOBS       |      |      STORIES        |
                                       |     (Queue)     |      |      (State)        |
                                       +-----------------+      +---------------------+
                                               |
                                               | (Poll for jobs)
                 +-----------------------------+--------------------------------+
                 |                             |                                |
                 v                             v                                v
        +--------+--------+           +--------+--------+             +----------+----------+
        |  Script Worker  |           |  Image Worker   |             |    Audio Worker     |
        |   (Gemini)      |           |   (Imagen 4)    |             |    (Google TTS)     |
        +-----------------+           +-----------------+             +---------------------+
                 |                             |                                |
                 |                             |                                |
                 v                             v                                v
        +--------+--------+           +--------+--------+             +----------+----------+
        | Metadata Worker |           |  Render Worker  |             |   Upload Worker     |
        |   (Gemini)      |           |    (FFmpeg)     |             | (YouTube API)       |
        +-----------------+           +-----------------+             +---------------------+

```

## 2. Worker Descriptions

The system is composed of several independent workers, each responsible for a specific task in the video creation pipeline. They poll the `jobs` table for tasks.

-   **Script Worker:**
    -   **Job Type:** `generate_script`
    -   **Action:** Takes a `topic` from a `story` and uses a generative AI (Gemini) to write a complete script. It then breaks the script down into individual `scenes`.
    -   **Output:** Updates the `story` with the full `script_text` and creates multiple `scenes` entries linked to the story.

-   **Image Worker:**
    -   **Job Type:** `generate_images`
    -   **Action:** For each `scene` in a story, it generates an image prompt and uses an image generation model (Imagen 4) to create a visual.
    -   **Output:** Uploads the generated image to Supabase Storage and updates the `image_url` in the corresponding `scene`.

-   **Audio Worker:**
    -   **Job Type:** `generate_audio`
    -   **Action:** For each `scene`, it converts the `text_content` into speech using Google TTS.
    -   **Output:** Uploads the generated audio file to Supabase Storage and updates the `audio_url` in the `scene`.

-   **Metadata Worker:**
    -   **Job Type:** `generate_metadata`
    -   **Action:** Uses a generative AI (Gemini) to create a compelling title, description, and list of tags for the video based on the script.
    -   **Output:** Updates the `metadata` JSONB field in the `story`.

-   **Render Worker:**
    -   **Job Type:** `render_video`
    -   **Action:** Downloads all scene images and audio files. Uses FFmpeg to stitch them together into a final video file, adding subtitles and background music.
    -   **Output:** Creates the final `video.mp4` and uploads it as an `asset`.

-   **Upload Worker:**
    -   **Job Type:** `upload_youtube`
    -   **Action:** Uploads the final rendered video to the "The Lost Archives" YouTube channel using the YouTube Data API.
    -   **Output:** Updates the `story` with the `youtube_url` and `youtube_video_id`.

## 3. State Flows

### Story Status Flow

A `story` progresses through a series of statuses, indicating its current stage in the pipeline.

`pending` → `generating_script` → `generating_images` → `generating_audio` → `generating_subtitles` → `generating_metadata` → `rendering` → `uploading` → `published`

-   If any step fails, the status changes to `failed`, and an `error_message` is logged.

### Job Status Flow

Each `job` has a simpler lifecycle.

`queued` → `processing` → `completed` | `failed`

-   A worker picks up a `queued` job and sets its status to `processing`.
-   Upon successful completion, the status becomes `completed`.
-   If an error occurs, the status becomes `failed`, and details are logged.

## 4. API Endpoints

A simple API is exposed to manage stories.

-   `POST /stories`
    -   **Description:** Creates a new story and kicks off the pipeline.
    -   **Body:** `{ "topic": "The History of the Roman Empire", "language": "en-US" }`
    -   **Response:** `{ "story_id": "...", "status": "pending" }`

-   `GET /stories/{story_id}`
    -   **Description:** Retrieves the current status and details of a story.
    -   **Response:** The full `story` object from the database.

-   `GET /stories`
    -   **Description:** Lists all stories with pagination.

## 5. Technical Decisions

-   **Database as a Queue:** Using a `jobs` table in PostgreSQL is simple and effective for this scale. It avoids the need for a separate message broker like RabbitMQ or SQS initially, simplifying the architecture.
-   **Supabase:** Provides a managed PostgreSQL database, authentication, and file storage in one platform, which is ideal for rapid development. The client libraries are easy to use from the Python workers.
-   **Independent Workers:** Decoupling each step into a separate worker (e.g., running as a separate Cloud Run service or Kubernetes pod) allows for independent scaling, updating, and error handling. If the image worker fails, it doesn't stop the script worker from processing other tasks.
-   **Idempotency:** Workers should be designed to be idempotent where possible. If a job fails and is retried, it should not cause duplicate data or errors.
-   **State Management:** The `status` fields in the `stories` and `jobs` tables provide a clear and auditable trail of the video creation process.
