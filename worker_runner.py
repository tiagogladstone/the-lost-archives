"""
Worker Runner - Runs all workers in a single process using multiprocessing.
Each worker runs in its own subprocess, polling for jobs.
"""
import multiprocessing
import os
import signal
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s')
logger = logging.getLogger('WorkerRunner')

# Import all workers
from workers.script_worker import ScriptWorker
from workers.image_worker import ImageWorker
from workers.audio_worker import AudioWorker
from workers.translation_worker import TranslationWorker
from workers.render_worker import RenderWorker
from workers.thumbnail_worker import ThumbnailWorker
from workers.metadata_worker import MetadataWorker
from workers.upload_worker import UploadWorker

WORKERS = [
    ScriptWorker,
    ImageWorker,
    AudioWorker,
    TranslationWorker,
    RenderWorker,
    ThumbnailWorker,
    MetadataWorker,
    UploadWorker,
]

def run_worker(worker_class):
    """Instantiate and run a single worker."""
    try:
        worker = worker_class()
        worker.run(poll_interval=10)
    except Exception as e:
        logger.error(f"Worker {worker_class.__name__} crashed: {e}")
        raise

def main():
    logger.info(f"Starting {len(WORKERS)} workers...")
    
    processes = []
    for worker_class in WORKERS:
        p = multiprocessing.Process(
            target=run_worker, 
            args=(worker_class,),
            name=worker_class.__name__
        )
        p.daemon = True
        p.start()
        processes.append((worker_class.__name__, p))
        logger.info(f"Started {worker_class.__name__} (PID: {p.pid})")
    
    # Also start a simple HTTP health check server for Cloud Run
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            # Check if all worker processes are alive
            alive = all(p.is_alive() for _, p in processes)
            status = 200 if alive else 503
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            workers_status = {name: p.is_alive() for name, p in processes}
            import json
            self.wfile.write(json.dumps({
                'status': 'healthy' if alive else 'unhealthy',
                'workers': workers_status
            }).encode())
        
        def log_message(self, format, *args):
            pass  # Suppress access logs
    
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    logger.info(f"Health check server on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        for name, p in processes:
            p.terminate()
        server.shutdown()

if __name__ == '__main__':
    main()
