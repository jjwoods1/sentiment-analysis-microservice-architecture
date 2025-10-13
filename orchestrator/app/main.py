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

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Audio Processing Orchestrator API")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3200", "http://localhost:3000", "http://10.1.0.35:3200"],
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
        db.execute("SELECT 1")
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
async def get_analytics_overview(db: Session = Depends(get_db)):
    """
    Get overall analytics overview.

    Returns:
        - Total calls processed
        - Total competitors found
        - Top competitors
        - Sentiment distribution
    """
    from sqlalchemy import func, case

    # Total jobs
    total_jobs = db.query(func.count(models.Job.id)).filter(
        models.Job.status == models.JobStatus.COMPLETED
    ).scalar() or 0

    # Total unique competitors mentioned
    total_competitors = db.query(func.count(func.distinct(models.SentimentResult.competitor_name))).scalar() or 0

    # Top 10 mentioned competitors
    top_competitors = db.query(
        models.SentimentResult.competitor_name,
        func.count(models.SentimentResult.id).label('mention_count')
    ).group_by(
        models.SentimentResult.competitor_name
    ).order_by(
        func.count(models.SentimentResult.id).desc()
    ).limit(10).all()

    # Overall sentiment distribution
    sentiment_distribution = db.query(
        func.jsonb_extract_path_text(models.SentimentResult.result_json, 'overall_sentiment').label('sentiment'),
        func.count(models.SentimentResult.id).label('count')
    ).group_by('sentiment').all()

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
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for a specific competitor.

    Returns:
        - Total mentions
        - Sentiment breakdown
        - Percentage of each sentiment
        - Number of calls where mentioned
    """
    from sqlalchemy import func

    # Total mentions
    total_mentions = db.query(func.count(models.SentimentResult.id)).filter(
        models.SentimentResult.competitor_name == competitor_name
    ).scalar() or 0

    if total_mentions == 0:
        raise HTTPException(status_code=404, detail=f"No data found for competitor: {competitor_name}")

    # Sentiment breakdown
    sentiment_breakdown = db.query(
        func.jsonb_extract_path_text(models.SentimentResult.result_json, 'overall_sentiment').label('sentiment'),
        func.count(models.SentimentResult.id).label('count')
    ).filter(
        models.SentimentResult.competitor_name == competitor_name
    ).group_by('sentiment').all()

    # Number of unique calls
    unique_calls = db.query(func.count(func.distinct(models.SentimentResult.job_id))).filter(
        models.SentimentResult.competitor_name == competitor_name
    ).scalar() or 0

    # Calculate percentages
    sentiment_data = []
    for sentiment, count in sentiment_breakdown:
        percentage = round((count / total_mentions) * 100, 2) if total_mentions > 0 else 0
        sentiment_data.append({
            "sentiment": sentiment or "unknown",
            "count": count,
            "percentage": percentage
        })

    return {
        "competitor_name": competitor_name,
        "total_mentions": total_mentions,
        "unique_calls": unique_calls,
        "sentiment_breakdown": sentiment_data
    }


@app.get("/analytics/competitors/list")
async def get_all_competitors(db: Session = Depends(get_db)):
    """
    Get list of all competitors that have been mentioned.
    """
    from sqlalchemy import func

    competitors = db.query(
        models.SentimentResult.competitor_name,
        func.count(models.SentimentResult.id).label('mention_count')
    ).group_by(
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
        func.jsonb_extract_path_text(models.SentimentResult.result_json, 'overall_sentiment').label('sentiment'),
        func.count(models.SentimentResult.id).label('count')
    )

    if competitor_name:
        query = query.filter(models.SentimentResult.competitor_name == competitor_name)

    trends = query.group_by('date', 'sentiment').order_by('date').all()

    return {
        "trends": [
            {
                "date": str(date),
                "sentiment": sentiment or "unknown",
                "count": count
            } for date, sentiment, count in trends
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
