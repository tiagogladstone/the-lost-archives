from fastapi import FastAPI, HTTPException, Header, Depends, Query
from pydantic import BaseModel
from supabase import create_client, Client
from typing import List, Optional
import os
import uuid
from . import models

app = FastAPI(
    title="The Lost Archives API",
    version="2.0",
    description="API to manage the story creation pipeline for The Lost Archives.",
)

# --- Supabase & Auth Setup ---

try:
    supabase_url = os.environ['SUPABASE_URL']
    supabase_key = os.environ['SUPABASE_KEY']
    supabase: Client = create_client(supabase_url, supabase_key)
except KeyError:
    raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in the environment.")

API_KEY = os.environ.get('API_KEY', 'dev-key-change-me')

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

# Dependency for API key verification
API_KEY_DEP = Depends(verify_api_key)

# --- Helper Functions ---

def get_story_or_404(story_id: uuid.UUID):
    """Fetches a story by ID or raises a 404 exception."""
    story_res = supabase.table("stories").select("*").eq("id", story_id).single().execute()
    if not story_res.data:
        raise HTTPException(status_code=404, detail=f"Story with id {story_id} not found.")
    return story_res.data

# --- API Endpoints ---

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/stories", response_model=models.StoryResponse, status_code=201, dependencies=[API_KEY_DEP])
async def create_story(story_data: models.CreateStoryRequest):
    """
    Creates a new story and enqueues the first job to generate the script.
    """
    try:
        # 1. Create the story in the database
        story_res = supabase.table("stories").insert({
            "topic": story_data.topic,
            "description": story_data.description,
            "target_duration_minutes": story_data.target_duration_minutes,
            "languages": story_data.languages,
            "status": "generating_script" # Initial status
        }).execute()

        if not story_res.data:
            raise HTTPException(status_code=500, detail="Failed to create story record.")

        story = story_res.data[0]
        story_id = story['id']

        # 2. Create the initial 'generate_script' job
        job_res = supabase.table("jobs").insert({
            "story_id": story_id,
            "job_type": "generate_script",
            "status": "queued"
        }).execute()

        if not job_res.data:
            # Attempt to roll back story creation for consistency
            supabase.table("stories").delete().eq("id", story_id).execute()
            raise HTTPException(status_code=500, detail="Failed to create initial job.")

        return story

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stories", response_model=List[models.StoryResponse], dependencies=[API_KEY_DEP])
async def list_stories(
    status: Optional[str] = Query(None),
    limit: int = Query(20, gt=0, le=100),
    offset: int = Query(0, ge=0)
):
    """
    Lists stories with optional filtering by status and pagination.
    """
    query = supabase.table("stories").select("id, topic, status, created_at, updated_at").order("created_at", desc=True)
    if status:
        query = query.eq("status", status)
    
    query = query.limit(limit).offset(offset)
    response = query.execute()
    
    return response.data

@app.get("/stories/{story_id}", response_model=models.StoryDetailResponse, dependencies=[API_KEY_DEP])
async def get_story_details(story_id: uuid.UUID):
    """
    Retrieves detailed information for a single story, including its scenes and options.
    """
    story = get_story_or_404(story_id)

    # Fetch related data in parallel
    scenes_res = supabase.table("scenes").select("*").eq("story_id", story_id).order("scene_order", desc=False).execute()
    titles_res = supabase.table("title_options").select("*").eq("story_id", story_id).execute()
    thumbnails_res = supabase.table("thumbnail_options").select("*").eq("story_id", story_id).execute()

    story["scenes"] = scenes_res.data
    story["title_options"] = titles_res.data
    story["thumbnail_options"] = thumbnails_res.data

    return story

@app.get("/stories/{story_id}/review", response_model=models.ReviewDataResponse, dependencies=[API_KEY_DEP])
async def get_review_data(story_id: uuid.UUID):
    """
    Gets all the necessary data for the human review page.
    """
    story = get_story_or_404(story_id)

    if story['status'] != 'ready_for_review':
        raise HTTPException(status_code=400, detail=f"Story is not ready for review. Current status: {story['status']}")

    titles_res = supabase.table("title_options").select("id, title_text").eq("story_id", story_id).execute()
    thumbnails_res = supabase.table("thumbnail_options").select("id, image_url, version").eq("story_id", story_id).execute()

    return {
        "story_id": story_id,
        "video_url": story.get("video_url"),
        "title_options": titles_res.data,
        "thumbnail_options": thumbnails_res.data,
        "metadata": story.get("metadata", {})
    }

@app.post("/stories/{story_id}/select-title", response_model=models.StoryDetailResponse, dependencies=[API_KEY_DEP])
async def select_title(story_id: uuid.UUID, request: models.SelectTitleRequest):
    """
    Selects a title for a story.
    """
    get_story_or_404(story_id) # Ensure story exists

    title_option_res = supabase.table("title_options").select("title_text").eq("id", request.title_option_id).eq("story_id", story_id).single().execute()
    if not title_option_res.data:
        raise HTTPException(status_code=404, detail="Title option not found for this story.")

    updated_story_res = supabase.table("stories").update({
        "selected_title": title_option_res.data['title_text']
    }).eq("id", story_id).select("*").single().execute()

    return await get_story_details(story_id)

@app.post("/stories/{story_id}/select-thumbnail", response_model=models.StoryDetailResponse, dependencies=[API_KEY_DEP])
async def select_thumbnail(story_id: uuid.UUID, request: models.SelectThumbnailRequest):
    """
    Selects a thumbnail for a story.
    """
    get_story_or_404(story_id) # Ensure story exists
    
    thumb_option_res = supabase.table("thumbnail_options").select("image_url").eq("id", request.thumbnail_option_id).eq("story_id", story_id).single().execute()
    if not thumb_option_res.data:
        raise HTTPException(status_code=404, detail="Thumbnail option not found for this story.")

    updated_story_res = supabase.table("stories").update({
        "selected_thumbnail_url": thumb_option_res.data['image_url']
    }).eq("id", story_id).select("*").single().execute()

    return await get_story_details(story_id)

@app.post("/stories/{story_id}/thumbnails/{thumb_id}/feedback", status_code=202, dependencies=[API_KEY_DEP])
async def regenerate_thumbnail_with_feedback(story_id: uuid.UUID, thumb_id: uuid.UUID, request: models.ThumbnailFeedbackRequest):
    """
    Provides feedback on a thumbnail and creates a job to regenerate it.
    """
    get_story_or_404(story_id) # Ensure story exists

    # Fetch the specific thumbnail to update its history
    thumb_res = supabase.table("thumbnail_options").select("*").eq("id", thumb_id).eq("story_id", story_id).single().execute()
    if not thumb_res.data:
        raise HTTPException(status_code=404, detail="Thumbnail option not found for this story.")
    
    # Append feedback to history
    current_feedback = thumb_res.data.get('feedback_history', [])
    current_feedback.append(request.feedback)
    
    supabase.table("thumbnail_options").update({"feedback_history": current_feedback}).eq("id", thumb_id).execute()

    # Create a regeneration job (the worker will handle the rest)
    supabase.table("jobs").insert({
        "story_id": story_id,
        "job_type": "regenerate_thumbnail",
        "status": "queued",
        # NOTE: 'payload' is not in the provided schema.sql, but is necessary
        # for the worker to know which thumbnail to regenerate and with what context.
        # Assuming the jobs table will be altered to include a JSONB 'payload' column.
        "payload": {"thumbnail_option_id": str(thumb_id), "feedback": request.feedback}
    }).execute()
    
    return {"message": "Thumbnail regeneration job created."}


@app.post("/stories/{story_id}/publish", response_model=models.PublishStatusResponse, dependencies=[API_KEY_DEP])
async def publish_story(story_id: uuid.UUID):
    """
    Checks if a story is ready and enqueues a job to publish it to YouTube.
    """
    story = get_story_or_404(story_id)

    if story['status'] != 'ready_for_review':
        raise HTTPException(status_code=400, detail=f"Story is not in a publishable state. Current status: {story['status']}")

    if not story.get('selected_title') or not story.get('selected_thumbnail_url'):
        raise HTTPException(status_code=400, detail="A title and thumbnail must be selected before publishing.")

    # Update status to 'publishing' and create job
    supabase.table("stories").update({"status": "publishing"}).eq("id", story_id).execute()
    supabase.table("jobs").insert({
        "story_id": story_id,
        "job_type": "upload_youtube",
        "status": "queued"
    }).execute()

    return {"status": "publishing", "message": "Story has been queued for publishing."}


@app.post("/stories/{story_id}/retry", status_code=202, dependencies=[API_KEY_DEP])
async def retry_failed_story(story_id: uuid.UUID):
    """
    Retries a failed story by re-enqueuing the last failed job.
    """
    story = get_story_or_404(story_id)
    if story['status'] != 'failed':
        raise HTTPException(status_code=400, detail=f"Story status is not 'failed'. Nothing to retry.")

    # Find the last failed job for this story
    last_failed_job_res = supabase.table("jobs").select("*").eq("story_id", story_id).eq("status", "failed").order("created_at", desc=True).limit(1).single().execute()
    
    if not last_failed_job_res.data:
        raise HTTPException(status_code=404, detail="No failed job found for this story to retry.")

    failed_job = last_failed_job_res.data
    
    # Re-enqueue the job by updating its status
    supabase.table("jobs").update({
        "status": "queued", 
        "error_message": None, 
        "worker_id": None
    }).eq("id", failed_job['id']).execute()

    # Reset the story status to the one before it failed (e.g., 'producing', 'rendering')
    # This is a simplification; a more robust system might store pre-failure status.
    # For now, we find the job type and guess the status.
    job_type_to_status = {
        "generate_script": "generating_script",
        "generate_image": "producing",
        "generate_audio": "producing",
        "translate_scene": "producing",
        "render_video": "rendering",
        "generate_thumbnails": "rendering",
        "generate_metadata": "rendering",
        "upload_youtube": "publishing"
    }
    previous_status = job_type_to_status.get(failed_job['job_type'], 'pending')
    
    supabase.table("stories").update({"status": previous_status, "error_message": None}).eq("id", story_id).execute()

    return {"message": f"Job {failed_job['id']} of type {failed_job['job_type']} has been re-queued."}


@app.delete("/stories/{story_id}", status_code=204, dependencies=[API_KEY_DEP])
async def delete_story(story_id: uuid.UUID):
    """
    Deletes a story and all its related data (cascades in DB).
    Note: This does not delete files from storage buckets. A background job would be needed for that.
    """
    story = get_story_or_404(story_id) # Ensure it exists before deleting
    
    # The ON DELETE CASCADE in the schema will handle deleting related scenes, options, and jobs.
    supabase.table("stories").delete().eq("id", story_id).execute()
    
    return
