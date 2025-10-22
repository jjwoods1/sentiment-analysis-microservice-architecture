from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from uuid import UUID
import httpx
import tempfile
import os
from typing import List, Dict, Any
import logging
from datetime import datetime

from . import crud, models, schemas
from .database import engine, get_db
from .config import settings
from .dependencies import verify_api_key
from .tasks import process_audio_pipeline
from .celery_app import celery_app
from .routers import patterns

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audio Processing Orchestrator API")

# Include routers
app.include_router(patterns.router)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3200", "http://localhost:3000", "http://10.1.0.35:3200", "http://10.1.0.35:3210"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "Audio Processing Orchestrator"}


@app.get("/health")
async def health_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Comprehensive health check endpoint.
    Checks database, Redis, MinIO, and dependent services.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "orchestrator-api",
        "checks": {}
    }

    all_healthy = True

    # Check Database
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "PostgreSQL connection successful"
        }
        logger.info("Health check: Database is healthy")
    except Exception as e:
        all_healthy = False
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        logger.error(f"Health check: Database is unhealthy - {str(e)}")

    # Check Redis (Celery broker)
    try:
        celery_inspect = celery_app.control.inspect()
        active_workers = celery_inspect.active()
        if active_workers:
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "message": "Redis connection successful",
                "workers": len(active_workers)
            }
            logger.info(f"Health check: Redis is healthy with {len(active_workers)} workers")
        else:
            all_healthy = False
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "message": "No active Celery workers found"
            }
            logger.warning("Health check: No active Celery workers")
    except Exception as e:
        all_healthy = False
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        logger.error(f"Health check: Redis is unhealthy - {str(e)}")

    # Check Storage Service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.STORAGE_URL}/health")
            if response.status_code == 200:
                health_status["checks"]["storage_service"] = {
                    "status": "healthy",
                    "message": "Storage service is reachable"
                }
                logger.info("Health check: Storage service is healthy")
            else:
                all_healthy = False
                health_status["checks"]["storage_service"] = {
                    "status": "unhealthy",
                    "message": f"Storage service returned {response.status_code}"
                }
                logger.warning(f"Health check: Storage service returned {response.status_code}")
    except Exception as e:
        all_healthy = False
        health_status["checks"]["storage_service"] = {
            "status": "unhealthy",
            "message": f"Storage service unreachable: {str(e)}"
        }
        logger.error(f"Health check: Storage service is unhealthy - {str(e)}")

    # Check Analysis Service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ANALYSIS_URL}/health")
            if response.status_code == 200:
                health_status["checks"]["analysis_service"] = {
                    "status": "healthy",
                    "message": "Analysis service is reachable"
                }
                logger.info("Health check: Analysis service is healthy")
            else:
                all_healthy = False
                health_status["checks"]["analysis_service"] = {
                    "status": "unhealthy",
                    "message": f"Analysis service returned {response.status_code}"
                }
                logger.warning(f"Health check: Analysis service returned {response.status_code}")
    except Exception as e:
        all_healthy = False
        health_status["checks"]["analysis_service"] = {
            "status": "unhealthy",
            "message": f"Analysis service unreachable: {str(e)}"
        }
        logger.error(f"Health check: Analysis service is unhealthy - {str(e)}")

    # Check Notification Service
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.NOTIFICATION_URL}/health")
            if response.status_code == 200:
                health_status["checks"]["notification_service"] = {
                    "status": "healthy",
                    "message": "Notification service is reachable"
                }
                logger.info("Health check: Notification service is healthy")
            else:
                all_healthy = False
                health_status["checks"]["notification_service"] = {
                    "status": "unhealthy",
                    "message": f"Notification service returned {response.status_code}"
                }
                logger.warning(f"Health check: Notification service returned {response.status_code}")
    except Exception as e:
        all_healthy = False
        health_status["checks"]["notification_service"] = {
            "status": "unhealthy",
            "message": f"Notification service unreachable: {str(e)}"
        }
        logger.error(f"Health check: Notification service is unhealthy - {str(e)}")

    # Set overall status
    health_status["status"] = "healthy" if all_healthy else "unhealthy"

    # Return appropriate HTTP status code
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return health_status if all_healthy else HTTPException(
        status_code=status_code,
        detail=health_status
    ).detail


@app.post("/upload", response_model=schemas.UploadResponse)
async def upload_audio(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an audio file for processing.

    1. Creates a job record
    2. Calls the audio split service
    3. Triggers background processing
    4. Returns job_id for status tracking
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Create job record
    job = crud.create_job(db, filename=file.filename)

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        # Call audio split service
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(tmp_file_path, 'rb') as f:
                files = {'file': (file.filename, f, file.content_type or 'audio/mpeg')}
                response = await client.post(f"{settings.SPLIT_URL}/split", files=files)
                response.raise_for_status()
                result = response.json()

                # Handle array response format
                if isinstance(result, list) and len(result) > 0:
                    split_result = result[0]
                else:
                    split_result = result

        # Clean up temporary file
        os.unlink(tmp_file_path)

        # Update job with channel URLs (may include base URL)
        left_url = split_result['left_channel_url']
        right_url = split_result['right_channel_url']

        # If URLs are relative paths, prepend the split service URL
        if not left_url.startswith('http'):
            left_url = f"{settings.SPLIT_URL}{left_url}"
        if not right_url.startswith('http'):
            right_url = f"{settings.SPLIT_URL}{right_url}"

        crud.update_job_channel_urls(
            db,
            job.id,
            left_url,
            right_url
        )

        # Update status to processing
        crud.update_job_status(db, job.id, models.JobStatus.PROCESSING)

        # Trigger background processing
        process_audio_pipeline.delay(str(job.id))

        return schemas.UploadResponse(
            job_id=job.id,
            message="Audio file uploaded and processing started",
            status=models.JobStatus.PROCESSING
        )

    except httpx.HTTPError as e:
        # Update job status to failed
        crud.update_job_status(
            db,
            job.id,
            models.JobStatus.FAILED,
            error_message=f"Audio split service error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to split audio: {str(e)}"
        )
    except Exception as e:
        # Update job status to failed
        crud.update_job_status(
            db,
            job.id,
            models.JobStatus.FAILED,
            error_message=f"Upload error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@app.post("/webhook", response_model=schemas.UploadResponse, dependencies=[Depends(verify_api_key)])
async def webhook(
    request: schemas.WebhookRequest,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for programmatic audio processing.
    Secured with X-API-KEY header.
    """
    # Create job record
    job = crud.create_job(db, filename=request.filename)

    try:
        # If file_url provided, download and process
        if request.file_url:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Download file
                file_response = await client.get(request.file_url)
                file_response.raise_for_status()

                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(request.filename)[1]) as tmp_file:
                    tmp_file.write(file_response.content)
                    tmp_file_path = tmp_file.name

                # Call audio split service
                with open(tmp_file_path, 'rb') as f:
                    files = {'file': (request.filename, f, 'audio/mpeg')}
                    split_response = await client.post(f"{settings.SPLIT_URL}/split", files=files)
                    split_response.raise_for_status()
                    result = split_response.json()

                    # Handle array response format
                    if isinstance(result, list) and len(result) > 0:
                        split_result = result[0]
                    else:
                        split_result = result

                # Clean up temporary file
                os.unlink(tmp_file_path)
        else:
            raise HTTPException(status_code=400, detail="file_url is required for webhook")

        # Update job with channel URLs (may include base URL)
        left_url = split_result['left_channel_url']
        right_url = split_result['right_channel_url']

        # If URLs are relative paths, prepend the split service URL
        if not left_url.startswith('http'):
            left_url = f"{settings.SPLIT_URL}{left_url}"
        if not right_url.startswith('http'):
            right_url = f"{settings.SPLIT_URL}{right_url}"

        crud.update_job_channel_urls(
            db,
            job.id,
            left_url,
            right_url
        )

        # Update status to processing
        crud.update_job_status(db, job.id, models.JobStatus.PROCESSING)

        # Trigger background processing
        process_audio_pipeline.delay(str(job.id))

        return schemas.UploadResponse(
            job_id=job.id,
            message="Webhook received and processing started",
            status=models.JobStatus.PROCESSING
        )

    except Exception as e:
        # Update job status to failed
        crud.update_job_status(
            db,
            job.id,
            models.JobStatus.FAILED,
            error_message=f"Webhook error: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


@app.get("/jobs", response_model=schemas.JobListResponse)
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get paginated list of all jobs.
    """
    jobs = crud.get_jobs(db, skip=skip, limit=limit)
    total = crud.get_jobs_count(db)
    return schemas.JobListResponse(total=total, jobs=jobs)


@app.get("/jobs/{job_id}", response_model=schemas.JobResponse)
async def get_job(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific job.
    """
    job = crud.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/analytics/overview")
async def get_analytics_overview(
    start_date: str = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get overall analytics overview.

    Returns:
        - Total calls processed
        - Total competitors found
        - Top competitors
        - Sentiment distribution

    Query Parameters:
        - start_date: Filter results from this date (inclusive)
        - end_date: Filter results until this date (inclusive)
    """
    from sqlalchemy import func, case
    from datetime import datetime as dt

    # Build date filters
    job_filters = [models.Job.status == models.JobStatus.COMPLETED]
    sentiment_filters = []

    if start_date:
        try:
            start_dt = dt.fromisoformat(start_date)
            job_filters.append(models.Job.created_at >= start_dt)
            sentiment_filters.append(models.SentimentResult.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end_dt = dt.fromisoformat(end_date)
            # Add one day to include the entire end date
            from datetime import timedelta
            end_dt = end_dt + timedelta(days=1)
            job_filters.append(models.Job.created_at < end_dt)
            sentiment_filters.append(models.SentimentResult.created_at < end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    # Total jobs
    total_jobs = db.query(func.count(models.Job.id)).filter(*job_filters).scalar() or 0

    # Total unique competitors mentioned (with date filter)
    query = db.query(func.count(func.distinct(models.SentimentResult.competitor_name)))
    if sentiment_filters:
        query = query.filter(*sentiment_filters)
    total_competitors = query.scalar() or 0

    # Top 10 mentioned competitors (with date filter)
    query = db.query(
        models.SentimentResult.competitor_name,
        func.count(models.SentimentResult.id).label('mention_count')
    )
    if sentiment_filters:
        query = query.filter(*sentiment_filters)
    top_competitors = query.group_by(
        models.SentimentResult.competitor_name
    ).order_by(
        func.count(models.SentimentResult.id).desc()
    ).limit(10).all()

    # Overall sentiment distribution (with date filter)
    query = db.query(
        models.SentimentResult.sentiment,
        func.count(models.SentimentResult.id).label('count')
    )
    if sentiment_filters:
        query = query.filter(*sentiment_filters)
    sentiment_distribution = query.group_by(models.SentimentResult.sentiment).all()

    return {
        "total_jobs": total_jobs,
        "total_competitors": total_competitors,
        "top_competitors": [
            {"name": comp, "count": count} for comp, count in top_competitors
        ],
        "sentiment_distribution": [
            {"sentiment": sent or "unknown", "count": count} for sent, count in sentiment_distribution
        ]
    }


@app.get("/analytics/competitor/{competitor_name}")
async def get_competitor_analytics(
    competitor_name: str,
    start_date: str = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for a specific competitor.

    Returns:
        - Total mentions
        - Sentiment breakdown
        - Percentage of each sentiment
        - Number of calls where mentioned
        - All individual segment results

    Query Parameters:
        - start_date: Filter results from this date (inclusive)
        - end_date: Filter results until this date (inclusive)
    """
    from sqlalchemy import func
    from datetime import datetime as dt

    # Build date filters
    filters = [models.SentimentResult.competitor_name == competitor_name]

    if start_date:
        try:
            start_dt = dt.fromisoformat(start_date)
            filters.append(models.SentimentResult.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end_dt = dt.fromisoformat(end_date)
            # Add one day to include the entire end date
            from datetime import timedelta
            end_dt = end_dt + timedelta(days=1)
            filters.append(models.SentimentResult.created_at < end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    # Total mentions
    total_mentions = db.query(func.count(models.SentimentResult.id)).filter(*filters).scalar() or 0

    if total_mentions == 0:
        raise HTTPException(status_code=404, detail=f"No data found for competitor: {competitor_name}")

    # Sentiment breakdown (now using direct sentiment column)
    sentiment_breakdown = db.query(
        models.SentimentResult.sentiment,
        func.count(models.SentimentResult.id).label('count')
    ).filter(*filters).group_by(models.SentimentResult.sentiment).all()

    # Number of unique calls
    unique_calls = db.query(func.count(func.distinct(models.SentimentResult.job_id))).filter(*filters).scalar() or 0

    # Calculate percentages
    sentiment_data = []
    for sentiment, count in sentiment_breakdown:
        percentage = round((count / total_mentions) * 100, 2) if total_mentions > 0 else 0
        sentiment_data.append({
            "sentiment": sentiment or "unknown",
            "count": count,
            "percentage": percentage
        })

    # Get all individual segment results for this competitor
    segments = db.query(models.SentimentResult).filter(*filters).order_by(models.SentimentResult.created_at.desc()).all()

    # Convert to dict format
    segments_data = []
    for segment in segments:
        segments_data.append({
            "id": str(segment.id),
            "job_id": str(segment.job_id),
            "segment_text": segment.segment_text,
            "sentiment": segment.sentiment,
            "detection_method": segment.detection_method,
            "detection_details": segment.detection_details,
            "segment_id": segment.segment_id,
            "start_time": segment.start_time,
            "end_time": segment.end_time,
            "created_at": segment.created_at.isoformat() if segment.created_at else None
        })

    return {
        "competitor_name": competitor_name,
        "total_mentions": total_mentions,
        "unique_calls": unique_calls,
        "sentiment_breakdown": sentiment_data,
        "segments": segments_data
    }


@app.get("/analytics/competitors/list")
async def get_all_competitors(
    start_date: str = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: str = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Get list of all competitors that have been mentioned.

    Query Parameters:
        - start_date: Filter results from this date (inclusive)
        - end_date: Filter results until this date (inclusive)
    """
    from sqlalchemy import func
    from datetime import datetime as dt

    # Build date filters
    filters = []

    if start_date:
        try:
            start_dt = dt.fromisoformat(start_date)
            filters.append(models.SentimentResult.created_at >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end_dt = dt.fromisoformat(end_date)
            # Add one day to include the entire end date
            from datetime import timedelta
            end_dt = end_dt + timedelta(days=1)
            filters.append(models.SentimentResult.created_at < end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    query = db.query(
        models.SentimentResult.competitor_name,
        func.count(models.SentimentResult.id).label('mention_count')
    )

    if filters:
        query = query.filter(*filters)

    competitors = query.group_by(
        models.SentimentResult.competitor_name
    ).order_by(
        models.SentimentResult.competitor_name
    ).all()

    return {
        "competitors": [
            {"name": comp, "mention_count": count} for comp, count in competitors
        ]
    }


@app.get("/analytics/sentiment-trends")
async def get_sentiment_trends(
    competitor_name: str = Query(None, description="Filter by specific competitor"),
    db: Session = Depends(get_db)
):
    """
    Get sentiment trends over time, optionally filtered by competitor.
    """
    from sqlalchemy import func, Date, cast

    query = db.query(
        cast(models.SentimentResult.created_at, Date).label('date'),
        models.SentimentResult.sentiment,
        func.count(models.SentimentResult.id).label('count')
    )

    if competitor_name:
        query = query.filter(models.SentimentResult.competitor_name == competitor_name)

    trends = query.group_by('date', models.SentimentResult.sentiment).order_by('date').all()

    return {
        "trends": [
            {
                "date": str(date),
                "sentiment": sentiment or "unknown",
                "count": count
            } for date, sentiment, count in trends
        ]
    }


@app.get("/admin/database/jobs")
async def get_all_jobs_raw(
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Get raw jobs table data for admin view.
    """
    jobs = db.query(models.Job).order_by(models.Job.created_at.desc()).limit(limit).all()

    return {
        "table": "jobs",
        "count": len(jobs),
        "rows": [
            {
                "id": str(job.id),
                "filename": job.filename,
                "status": job.status.value,
                "error_message": job.error_message,
                "left_channel_url": job.left_channel_url,
                "right_channel_url": job.right_channel_url,
                "left_transcript_path": job.left_transcript_path,
                "right_transcript_path": job.right_transcript_path,
                "competitors_found": job.competitors_found,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "updated_at": job.updated_at.isoformat() if job.updated_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None
            } for job in jobs
        ]
    }


@app.get("/admin/database/sentiment_results")
async def get_all_sentiment_results_raw(
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db)
):
    """
    Get raw sentiment_results table data for admin view.
    """
    results = db.query(models.SentimentResult).order_by(models.SentimentResult.created_at.desc()).limit(limit).all()

    return {
        "table": "sentiment_results",
        "count": len(results),
        "rows": [
            {
                "id": str(result.id),
                "job_id": str(result.job_id),
                "competitor_name": result.competitor_name,
                "segment_text": result.segment_text,
                "sentiment": result.sentiment,
                "detection_method": result.detection_method,
                "detection_details": result.detection_details,
                "segment_id": result.segment_id,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "context": result.context,
                "metadata_json": result.metadata_json,
                "created_at": result.created_at.isoformat() if result.created_at else None
            } for result in results
        ]
    }


@app.get("/admin/storage/files")
async def get_storage_files():
    """
    Get list of all files in MinIO storage.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{settings.STORAGE_URL}/list")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve storage files: {str(e)}"
        )


@app.get("/admin/storage/download/{object_path:path}")
async def download_transcript(object_path: str):
    """
    Download a transcript file from MinIO storage via storage service proxy.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{settings.STORAGE_URL}/download/{object_path}")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transcript not found: {object_path}"
            )
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Storage service error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download transcript: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
