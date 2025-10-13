from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from . import models, schemas


def create_job(db: Session, filename: str) -> models.Job:
    """Create a new job record."""
    db_job = models.Job(filename=filename, status=models.JobStatus.PENDING)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job


def get_job(db: Session, job_id: UUID) -> Optional[models.Job]:
    """Get a job by ID."""
    return db.query(models.Job).filter(models.Job.id == job_id).first()


def get_jobs(db: Session, skip: int = 0, limit: int = 100) -> List[models.Job]:
    """Get all jobs with pagination."""
    return db.query(models.Job).order_by(desc(models.Job.created_at)).offset(skip).limit(limit).all()


def get_jobs_count(db: Session) -> int:
    """Get total count of jobs."""
    return db.query(models.Job).count()


def update_job_status(
    db: Session,
    job_id: UUID,
    status: models.JobStatus,
    error_message: Optional[str] = None
) -> Optional[models.Job]:
    """Update job status and optionally set error message."""
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = status
        db_job.updated_at = datetime.utcnow()

        if error_message:
            db_job.error_message = error_message

        if status == models.JobStatus.COMPLETED:
            db_job.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(db_job)
    return db_job


def update_job_channel_urls(
    db: Session,
    job_id: UUID,
    left_channel_url: str,
    right_channel_url: str
) -> Optional[models.Job]:
    """Update job with audio channel URLs from split service."""
    db_job = get_job(db, job_id)
    if db_job:
        db_job.left_channel_url = left_channel_url
        db_job.right_channel_url = right_channel_url
        db_job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_job)
    return db_job


def update_job_transcript_paths(
    db: Session,
    job_id: UUID,
    left_transcript_path: Optional[str] = None,
    right_transcript_path: Optional[str] = None
) -> Optional[models.Job]:
    """Update job with transcript paths in MinIO."""
    db_job = get_job(db, job_id)
    if db_job:
        if left_transcript_path:
            db_job.left_transcript_path = left_transcript_path
        if right_transcript_path:
            db_job.right_transcript_path = right_transcript_path
        db_job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_job)
    return db_job


def update_job_competitors(
    db: Session,
    job_id: UUID,
    competitors: List[str]
) -> Optional[models.Job]:
    """Update job with found competitors."""
    db_job = get_job(db, job_id)
    if db_job:
        db_job.competitors_found = competitors
        db_job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_job)
    return db_job


def create_sentiment_result(
    db: Session,
    job_id: UUID,
    competitor_name: str,
    result_json: dict
) -> models.SentimentResult:
    """Create a sentiment analysis result for a job."""
    db_result = models.SentimentResult(
        job_id=job_id,
        competitor_name=competitor_name,
        result_json=result_json
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_sentiment_results_by_job(db: Session, job_id: UUID) -> List[models.SentimentResult]:
    """Get all sentiment results for a job."""
    return db.query(models.SentimentResult).filter(
        models.SentimentResult.job_id == job_id
    ).all()
