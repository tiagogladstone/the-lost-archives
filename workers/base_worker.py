import os
import time
import supabase
from abc import ABC, abstractmethod
from dotenv import load_dotenv

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
        self.supabase_client = self._init_supabase()
        print(f"[{self.worker_id}] Initialized for job type: {self.job_type}")

    def _init_supabase(self):
        """Initializes the Supabase client from environment variables."""
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment.")
        return supabase.create_client(supabase_url, supabase_key)

    def poll_for_job(self):
        """
        Polls the 'jobs' table for a single 'queued' job of the worker's type.
        If a job is found, it atomically updates its status to 'processing'
        and sets the worker_id.
        """
        try:
            # Use an RPC call to a Postgres function to ensure atomicity
            # This function would find a queued job, update its status and worker_id,
            # and return the job details.
            #
            # Example function `claim_job(job_type_in TEXT, worker_id_in TEXT)`:
            # See database/functions.sql for the actual implementation.
            # For now, we'll simulate this with a less-than-atomic select then update.

            response = self.supabase_client.table('jobs') \
                .select('*') \
                .eq('status', 'queued') \
                .eq('job_type', self.job_type) \
                .limit(1) \
                .execute()

            if response.data:
                job = response.data[0]
                print(f"[{self.worker_id}] Found job: {job['id']}")
                
                update_response = self.supabase_client.table('jobs') \
                    .update({
                        'status': 'processing',
                        'worker_id': self.worker_id,
                        'started_at': 'now()'
                    }) \
                    .eq('id', job['id']) \
                    .eq('status', 'queued') # Double-check to prevent race conditions
                    .execute()

                if update_response.data:
                    return update_response.data[0]
                else:
                    print(f"[{self.worker_id}] Failed to claim job {job['id']} (likely claimed by another worker).")
                    return None
            
            return None
        except Exception as e:
            print(f"[{self.worker_id}] Error polling for jobs: {e}")
            return None

    @abstractmethod
    def process(self, job):
        """
        The core logic of the worker. This method must be implemented by subclasses.
        It receives a job object and should perform the required task.
        """
        pass

    def run(self, poll_interval=5):
        """
        The main loop for the worker. Polls for jobs and processes them.
        """
        print(f"[{self.worker_id}] Starting worker loop...")
        while True:
            job = self.poll_for_job()
            if job:
                try:
                    print(f"[{self.worker_id}] Processing job: {job['id']}")
                    self.process(job)
                    
                    self.supabase_client.table('jobs') \
                        .update({
                            'status': 'completed',
                            'completed_at': 'now()'
                        }) \
                        .eq('id', job['id']) \
                        .execute()
                    
                    print(f"[{self.worker_id}] Successfully completed job: {job['id']}")

                except Exception as e:
                    print(f"[{self.worker_id}] Error processing job {job['id']}: {e}")
                    error_message = str(e)
                    self.supabase_client.table('jobs') \
                        .update({
                            'status': 'failed',
                            'error_message': error_message,
                            'completed_at': 'now()'
                        }) \
                        .eq('id', job['id']) \
                        .execute()
            else:
                # No job found, wait before polling again
                time.sleep(poll_interval)

if __name__ == '__main__':
    # This base class should not be run directly.
    print("This is a base worker class and cannot be run directly.")
    print("Implement a subclass and run that instead.")
