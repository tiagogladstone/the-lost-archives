from workers.base_worker import BaseWorker

class MetadataWorker(BaseWorker):
    """
    Worker responsible for generating video metadata (title, description, tags).
    It uses the full script_text of a story to generate compelling and
    SEO-friendly metadata using a generative AI model.
    """

    def __init__(self):
        super().__init__("generate_metadata")

    def process(self, job):
        """
        Processes a 'generate_metadata' job.

        1. Fetches the full 'script_text' for the story.
        2. Calls a generative AI model (e.g., Gemini) with a specific prompt
           to generate a title, description, and a list of relevant tags.
        3. Updates the 'metadata' JSONB field in the 'stories' table with the results.
        4. Updates the story status to the next step in the pipeline.
        """
        print(f"[{self.worker_id}] Starting metadata generation for story: {job['story_id']}")
        
        # This is a skeleton. The actual implementation will go here.
        # For now, we'll just log a message and succeed.
        pass

        print(f"[{self.worker_id}] Finished metadata generation for story: {job['story_id']}")

if __name__ == "__main__":
    try:
        worker = MetadataWorker()
        worker.run()
    except KeyboardInterrupt:
        print("MetadataWorker shutting down.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
