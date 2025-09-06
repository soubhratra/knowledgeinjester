#!/usr/bin/env python3
"""
Worker script for knowledge injester.
This can be used for background processing, Celery workers, or scheduled tasks.
"""
import os
import time
import logging
import django
from pathlib import Path

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "knowledgeinjester.settings")
django.setup()

from django.conf import settings
from apps.core.logging import get_logger
from apps.crawler.services import crawl_website_sync
from apps.tenants.models import CrawlJob, IngestJob

log = get_logger(__name__)


def process_pending_crawl_jobs():
    """Process pending crawl jobs."""
    pending_jobs = CrawlJob.objects.filter(status='pending')
    log.info(f"Found {pending_jobs.count()} pending crawl jobs")
    
    for job in pending_jobs:
        try:
            log.info(f"Processing crawl job {job.job_id}")
            job.status = 'running'
            job.save()
            
            # Run the crawl
            pages = crawl_website_sync(str(job.root_url), job.max_pages)
            
            # Update job status
            job.status = 'completed'
            job.result = {
                'pages_crawled': len(pages),
                'completed_at': time.time()
            }
            job.save()
            
            log.info(f"Completed crawl job {job.job_id}")
            
        except Exception as e:
            log.error(f"Failed to process crawl job {job.job_id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.save()


def process_pending_ingest_jobs():
    """Process pending ingest jobs."""
    pending_jobs = IngestJob.objects.filter(status='pending')
    log.info(f"Found {pending_jobs.count()} pending ingest jobs")
    
    for job in pending_jobs:
        try:
            log.info(f"Processing ingest job {job.job_id}")
            job.status = 'crawling'
            job.save()
            
            # Run the full pipeline
            pages = crawl_website_sync(str(job.root_url), job.max_pages)
            
            # Update job status
            job.status = 'completed'
            job.result = {
                'pages_crawled': len(pages),
                'completed_at': time.time()
            }
            job.save()
            
            log.info(f"Completed ingest job {job.job_id}")
            
        except Exception as e:
            log.error(f"Failed to process ingest job {job.job_id}: {e}")
            job.status = 'failed'
            job.error_message = str(e)
            job.save()


def run_worker():
    """Main worker function."""
    log.info("Worker started")
    
    try:
        # Process crawl jobs
        process_pending_crawl_jobs()
        
        # Process ingest jobs
        process_pending_ingest_jobs()
        
        log.info("Worker cycle completed")
        
    except Exception as e:
        log.error(f"Worker error: {e}")
        raise


def run_once():
    """Run worker once."""
    log.info("Worker started: single run")
    run_worker()
    log.info("Worker finished")


def run_continuous(interval: int = 60):
    """Run worker continuously with specified interval."""
    log.info(f"Worker started: continuous mode (interval: {interval}s)")
    
    try:
        while True:
            run_worker()
            time.sleep(interval)
    except KeyboardInterrupt:
        log.info("Worker stopped by user")
    except Exception as e:
        log.error(f"Worker error: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "continuous":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        run_continuous(interval)
    else:
        run_once()
