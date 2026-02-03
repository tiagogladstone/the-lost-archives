import os
import time
import supabase
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

class BaseWorker(ABC):
    """
    Abstract base class for all workers.
    Provides the core logic for polling for jobs, processing them,
    and updating their status in the Supabase database.
    """

    def __init__(self, job_type):
        self.job_type = job_type
        self.worker_id = f"{self.__class__.__name__}-{os.getpid()}"
        self.supabase = self._init_supabase()
        print(f"[{self.worker_id}] Initialized for job type: {self.job_type}")

    def _init_supabase(self):
        """Initializes the Supabase client from environment variables."""
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment.")
        return supabase.create_client(supabase_url, supabase_key)

    def claim_job(self):
        """Pega um job da fila de forma atômica (sem race condition)."""
        # Usar uma stored procedure no Supabase
        result = self.supabase.rpc('claim_next_job', {
            'p_job_type': self.job_type,
            'p_worker_id': self.worker_id
        }).execute()
        
        if result.data:
            job = result.data[0]
            print(f"[{self.worker_id}] Claimed job: {job['id']}")
            return job
        
        return None

    @abstractmethod
    def process(self, job):
        """
        The core logic of the worker. This method must be implemented by subclasses.
        It receives a job object and should perform the required task.
        """
        pass
    
    def get_job(self, job_id):
        """Fetches a job by its ID."""
        return self.supabase.table('jobs').select('*').eq('id', job_id).single().execute().data

    def handle_failure(self, job, error_message):
        """Trata falha de um job com retry automático."""
        # job data might be stale, refetch it
        job = self.get_job(job['id'])
        
        if job['retry_count'] < job['max_retries']:
            # Calcular backoff exponencial
            delay = 30 * (2 ** job['retry_count'])  # 30s, 60s, 120s
            next_retry = datetime.now() + timedelta(seconds=delay)
            print(f"[{self.worker_id}] Job {job['id']} failed. Retrying in {delay} seconds.")
            self.supabase.table('jobs').update({
                'status': 'queued',
                'retry_count': job['retry_count'] + 1,
                'next_retry_at': next_retry.isoformat(),
                'error_message': error_message,
                'worker_id': None, # Clear worker_id
                'started_at': None
            }).eq('id', job['id']).execute()
        else:
            # Max retries atingido
            print(f"[{self.worker_id}] Job {job['id']} failed. Max retries reached.")
            self.supabase.table('jobs').update({
                'status': 'failed',
                'error_message': f'Max retries reached. Last error: {error_message}',
                'completed_at': 'now()'
            }).eq('id', job['id']).execute()
            # Marcar story como failed
            if job.get('story_id'):
                self.supabase.table('stories').update({
                    'status': 'failed',
                    'error_message': f'Job {job["job_type"]} failed after {job["max_retries"]} retries'
                }).eq('id', job['story_id']).execute()

    def check_and_advance(self, story_id):
        """Verifica se a próxima fase pode começar e cria os jobs necessários."""
        print(f"[{self.worker_id}] Checking and advancing for story_id: {story_id}")
        story = self.supabase.table('stories').select('*').eq('id', story_id).single().execute()
        scenes_res = self.supabase.table('scenes').select('id,image_url,audio_url').eq('story_id', story_id).execute()
        
        scenes = scenes_res.data
        status = story.data['status']
        
        # This logic needs to be fully fleshed out based on the state machine
        if status == 'producing':
            total_scenes = len(scenes)
            if not total_scenes:
                print(f"[{self.worker_id}] No scenes found for story {story_id}, cannot advance.")
                return

            all_images = all(s.get('image_url') for s in scenes)
            all_audio = all(s.get('audio_url') for s in scenes)
            
            if all_images and all_audio:
                print(f"[{self.worker_id}] All images and audio are ready for story {story_id}. Advancing to rendering.")
                # self.create_job(story_id, 'render_video') # Placeholder for job creation logic
                # self.update_story_status(story_id, 'rendering') # Placeholder for status update
                # NOTE: Job creation and status updates should be handled by the specific worker
                # or a dedicated orchestrator function. This base worker should only check.
                # For this task, we will assume job creation is simple.
                self.supabase.table('jobs').insert({
                    'story_id': story_id,
                    'job_type': 'render_video' # Assuming this is the correct job type
                }).execute()
                self.supabase.table('stories').update({'status': 'rendering'}).eq('id', story_id).execute()
        
        elif status == 'rendering':
            # This part of the logic is not fully defined in the prompt, but we can infer it.
            # After rendering, we need to generate thumbnails and metadata.
            # We assume the 'render_worker' would have updated the story with a video_url.
            if story.data.get('video_url'):
                 print(f"[{self.worker_id}] Video is rendered for story {story_id}. Creating metadata and thumbnail jobs.")
                 self.supabase.table('jobs').insert([
                     {'story_id': story_id, 'job_type': 'generate_thumbnails'},
                     {'story_id': story_id, 'job_type': 'generate_metadata'}
                 ]).execute()
                 # A new status like 'post-production' might be needed, or we go straight to review
                 # once both jobs are done. Let's assume another check happens there.

        elif status == 'ready_for_review':
             # This phase is triggered by thumbnail and metadata workers finishing.
             # Let's check if they are done.
             thumbnails_res = self.supabase.table('thumbnail_options').select('id').eq('story_id', story_id).execute()
             titles_res = self.supabase.table('title_options').select('id').eq('story_id', story_id).execute()

             if len(thumbnails_res.data) > 0 and len(titles_res.data) > 0:
                 # Logic for what happens after metadata/thumbs are done is to set story to ready_for_review
                 # This should be done by the thumbnail/metadata workers themselves.
                 # Let's assume the status is already 'ready_for_review' and we are checking
                 # if we can move to 'publishing'. This is a human step, so no action here.
                 pass
        
        # Other state transitions would go here...


    def run(self, poll_interval=5):
        """
        The main loop for the worker. Polls for jobs and processes them.
        """
        print(f"[{self.worker_id}] Starting worker loop...")
        while True:
            job = self.claim_job()
            if job:
                try:
                    print(f"[{self.worker_id}] Processing job: {job['id']}")
                    
                    # The actual work is done here
                    self.process(job)
                    
                    self.supabase.table('jobs') \
                        .update({
                            'status': 'completed',
                            'completed_at': 'now()'
                        }) \
                        .eq('id', job['id']) \
                        .execute()
                    
                    print(f"[{self.worker_id}] Successfully completed job: {job['id']}")

                    # After completing a job, check if we can advance the story's state
                    if job.get('story_id'):
                        self.check_and_advance(job['story_id'])

                except Exception as e:
                    print(f"[{self.worker_id}] Error processing job {job['id']}: {e}")
                    error_message = str(e)
                    self.handle_failure(job, error_message)
            else:
                # No job found, wait before polling again
                time.sleep(poll_interval)

if __name__ == '__main__':
    # This base class should not be run directly.
    print("This is a base worker class and cannot be run directly.")
    print("Implement a subclass and run that instead.")
