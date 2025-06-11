from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone
import logging
from .analysis_s3 import upload_old_analyses

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create scheduler instance
scheduler = AsyncIOScheduler()

def upload_old_analyses_task():
    """Task to upload old analyses to S3"""
    try:
        logger.info(f"Starting periodic upload of old analyses at {datetime.now(timezone.utc)}")
        upload_old_analyses(hours_threshold=3)
        logger.info("Completed periodic upload of old analyses")
    except Exception as e:
        logger.error(f"Error in periodic upload task: {str(e)}")

def setup_scheduler():
    """Setup and start the scheduler with periodic tasks"""
    try:
        # Add the upload task to run every 6 hours
        scheduler.add_job(
            upload_old_analyses_task,
            trigger=IntervalTrigger(minutes=5),
            id='upload_old_analyses',
            name='Upload old analyses to S3',
            replace_existing=True,
            max_instances=1
        )
        
        # Start the scheduler
        scheduler.start()
        logger.info("Scheduler started successfully")
        
    except Exception as e:
        logger.error(f"Error setting up scheduler: {str(e)}")
        raise

def shutdown_scheduler():
    """Gracefully shutdown the scheduler"""
    try:
        scheduler.shutdown()
        logger.info("Scheduler shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down scheduler: {str(e)}")
        raise 