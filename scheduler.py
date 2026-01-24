import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

logger = logging.getLogger(__name__)

scheduler = None

def init_scheduler(app, db_uri):
    """Initialize the APScheduler with SQLAlchemy job store"""
    global scheduler
    
    jobstores = {
        'default': SQLAlchemyJobStore(url=db_uri)
    }
    
    scheduler = BackgroundScheduler(
        jobstores=jobstores,
        timezone='Europe/Istanbul'
    )
    
    return scheduler


def start_scheduler():
    """Start the scheduler"""
    global scheduler
    if scheduler and not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def stop_scheduler():
    """Stop the scheduler"""
    global scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def add_backup_job(site_id: int, interval_type: str, interval_value: int):
    """
    Add a scheduled backup job for a site
    
    Args:
        site_id: The site ID to backup
        interval_type: 'minutes', 'hours', 'days', 'weeks'
        interval_value: Number of intervals
    """
    global scheduler
    
    if not scheduler:
        logger.error("Scheduler not initialized")
        return False
    
    job_id = f"backup_site_{site_id}"
    
    # Remove existing job if any
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    
    # Calculate interval kwargs
    interval_kwargs = {interval_type: interval_value}
    
    # Add job
    scheduler.add_job(
        func='app:run_scheduled_backup',
        trigger='interval',
        id=job_id,
        args=[site_id],
        **interval_kwargs,
        next_run_time=datetime.now() + timedelta(**interval_kwargs),
        replace_existing=True
    )
    
    logger.info(f"Added backup job for site {site_id}: every {interval_value} {interval_type}")
    return True


def remove_backup_job(site_id: int):
    """Remove a scheduled backup job"""
    global scheduler
    
    if not scheduler:
        return False
    
    job_id = f"backup_site_{site_id}"
    
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed backup job for site {site_id}")
        return True
    except Exception as e:
        logger.warning(f"Could not remove job {job_id}: {e}")
        return False


def get_next_run_time(site_id: int):
    """Get the next scheduled run time for a site backup"""
    global scheduler
    
    if not scheduler:
        return None
    
    job_id = f"backup_site_{site_id}"
    job = scheduler.get_job(job_id)
    
    return job.next_run_time if job else None


def pause_backup_job(site_id: int):
    """Pause a backup job"""
    global scheduler
    
    if not scheduler:
        return False
    
    job_id = f"backup_site_{site_id}"
    
    try:
        scheduler.pause_job(job_id)
        return True
    except:
        return False


def resume_backup_job(site_id: int):
    """Resume a paused backup job"""
    global scheduler
    
    if not scheduler:
        return False
    
    job_id = f"backup_site_{site_id}"
    
    try:
        scheduler.resume_job(job_id)
        return True
    except:
        return False
