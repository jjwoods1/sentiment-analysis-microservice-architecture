from celery import chain, group
from celery.exceptions import MaxRetriesExceededError
import httpx
import json
import tempfile
import os
import traceback
from uuid import UUID
from datetime import datetime
import time

from .celery_app import celery_app
from .database import SessionLocal
from . import crud, models
from .config import settings


def send_notification(job_id: str, filename: str, error_message: str, task_name: str = None):
    """
    Send error notification to notification service.
    Non-blocking - failures are logged but don't affect the main task.
    """
    try:
        stack = traceback.format_exc()

        with httpx.Client(timeout=10.0) as client:
            if task_name:
                # Task-specific failure
                client.post(
                    f"{settings.NOTIFICATION_URL}/notify/task-failed",
                    json={
                        "task_name": task_name,
                        "job_id": job_id,
                        "error_message": error_message,
                        "stack_trace": stack
                    }
                )
            else:
                # Job-level failure
                client.post(
                    f"{settings.NOTIFICATION_URL}/notify/job-failed",
                    json={
                        "job_id": job_id,
                        "filename": filename,
                        "error_message": error_message,
                        "stack_trace": stack
                    }
                )
    except Exception as e:
        # Don't let notification failures break the main flow
        print(f"Failed to send notification: {str(e)}")


def get_auth_token(max_retries=3):
    """
    Get authentication token from auth service with retry logic.
    Response format: [{"access_token": "...", "token_type": "bearer"}]
    """
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{settings.AUTH_URL}/api/v1/login/access-token",
                    data={
                        "username": settings.AUTH_USERNAME,
                        "password": settings.AUTH_PASSWORD
                    }
                )
                response.raise_for_status()
                result = response.json()
                # Handle array response format
                if isinstance(result, list) and len(result) > 0:
                    return result[0]["access_token"]
                return result["access_token"]
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            # Exponential backoff
            time.sleep(2 ** attempt)
    return None


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def transcribe_audio_channel(self, job_id: str, channel_url: str, channel_name: str):
    """
    Transcribe a single audio channel with retry logic.

    Expected transcription response format:
    [{"success": true, "message": "...", "data": {"model": "...", "text": "...", "segments": [...]}}]

    Args:
        job_id: UUID of the job
        channel_url: URL to the audio channel file
        channel_name: 'left' or 'right'

    Returns:
        Storage path to the saved transcript
    """
    db = SessionLocal()

    try:
        # Get authentication token
        token = get_auth_token()

        # Download audio file and process transcription
        with httpx.Client(timeout=300.0) as client:
            audio_response = client.get(channel_url)
            audio_response.raise_for_status()

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_audio:
                tmp_audio.write(audio_response.content)
                tmp_audio_path = tmp_audio.name

            # Call transcription service with optimal Whisper parameters
            with open(tmp_audio_path, 'rb') as audio_file:
                files = {'audio_file': ('audio.mp3', audio_file, 'audio/mpeg')}
                data = {
                    'whisper_model': 'large-v3',
                    'compression_ratio_threshold': '1.8',
                    'temperature': '0',
                    'logprob_threshold': '-0.8',
                    'no_speech_threshold': '0.7',
                    'condition_on_previous_text': 'false',
                    'beam_size': '1',
                    'best_of': '1',
                    'word_timestamps': 'true',
                    'language': 'en'
                }
                headers = {'Authorization': f'Bearer {token}'}

                transcription_response = client.post(
                    f"{settings.TRANSCRIPTION_URL}/api/v1/transcriptions/",
                    files=files,
                    data=data,
                    headers=headers
                )
                transcription_response.raise_for_status()
                result = transcription_response.json()

                # Handle array response format
                if isinstance(result, list) and len(result) > 0:
                    transcript_data = result[0].get('data', result[0])
                else:
                    transcript_data = result

            # Clean up temporary audio file
            os.unlink(tmp_audio_path)

            # Save transcript to Storage Service
            transcript_path = f"transcripts/{job_id}/{channel_name}_transcript.json"

            storage_response = client.post(
                f"{settings.STORAGE_URL}/upload",
                json={
                    "object_path": transcript_path,
                    "data": transcript_data
                }
            )
            storage_response.raise_for_status()

        # Update job record with transcript path
        if channel_name == 'left':
            crud.update_job_transcript_paths(db, UUID(job_id), left_transcript_path=transcript_path)
        else:
            crud.update_job_transcript_paths(db, UUID(job_id), right_transcript_path=transcript_path)

        return transcript_path

    except Exception as e:
        db.close()
        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            # Get job details for notification
            job = crud.get_job(db, UUID(job_id))
            error_msg = f"Transcription failed for {channel_name} channel after 3 retries: {str(e)}"

            # Update job status to failed
            crud.update_job_status(
                db,
                UUID(job_id),
                models.JobStatus.FAILED,
                error_message=error_msg
            )

            # Send notification
            if job:
                send_notification(job_id, job.filename, error_msg, f"transcribe_audio_channel ({channel_name})")

            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_competitors(self, job_id: str, left_transcript_path: str, right_transcript_path: str):
    """
    Analyze transcripts for competitor mentions with retry logic.

    Args:
        job_id: UUID of the job
        left_transcript_path: Storage path to left channel transcript
        right_transcript_path: Storage path to right channel transcript

    Returns:
        List of competitor names found
    """
    db = SessionLocal()

    try:
        # Download both transcripts from Storage Service
        with httpx.Client(timeout=30.0) as client:
            left_response = client.get(f"{settings.STORAGE_URL}/download/{left_transcript_path}")
            left_response.raise_for_status()
            left_result = left_response.json()
            # Handle nested data structure: data.data.data
            left_data = left_result.get('data', {})
            if isinstance(left_data, dict) and 'data' in left_data:
                left_transcript = left_data.get('data', {})
            else:
                left_transcript = left_data

            right_response = client.get(f"{settings.STORAGE_URL}/download/{right_transcript_path}")
            right_response.raise_for_status()
            right_result = right_response.json()
            # Handle nested data structure: data.data.data
            right_data = right_result.get('data', {})
            if isinstance(right_data, dict) and 'data' in right_data:
                right_transcript = right_data.get('data', {})
            else:
                right_transcript = right_data

            # Combine transcript texts
            combined_text = left_transcript.get('text', '') + ' ' + right_transcript.get('text', '')

            # Call analysis service
            analysis_response = client.post(
                f"{settings.ANALYSIS_URL}/find-competitors",
                json={"transcript_text": combined_text}
            )
            analysis_response.raise_for_status()
            result = analysis_response.json()
            competitors_found = result.get('competitors_found', [])

        # Update job record with competitors
        crud.update_job_competitors(db, UUID(job_id), competitors_found)

        return competitors_found

    except Exception as e:
        db.close()
        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            # Get job details for notification
            job = crud.get_job(db, UUID(job_id))
            error_msg = f"Competitor analysis failed after 3 retries: {str(e)}"

            # Update job status to failed
            crud.update_job_status(
                db,
                UUID(job_id),
                models.JobStatus.FAILED,
                error_message=error_msg
            )

            # Send notification
            if job:
                send_notification(job_id, job.filename, error_msg, "analyze_competitors")

            raise
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_sentiment_for_competitor(self, job_id: str, competitor_name: str, left_transcript_path: str, right_transcript_path: str, filename: str = "unknown"):
    """
    Analyze sentiment for a specific competitor with retry logic.

    Expected sentiment response format: [] (empty array) or array with results

    Args:
        job_id: UUID of the job
        competitor_name: Name of the competitor to analyze
        left_transcript_path: Storage path to left channel transcript
        right_transcript_path: Storage path to right channel transcript
        filename: Original audio filename

    Returns:
        Sentiment analysis result
    """
    db = SessionLocal()

    try:
        # Download both transcripts from Storage Service
        with httpx.Client(timeout=120.0) as client:
            left_response = client.get(f"{settings.STORAGE_URL}/download/{left_transcript_path}")
            left_response.raise_for_status()
            left_result = left_response.json()
            # Handle nested data structure: data.data.data
            left_data = left_result.get('data', {})
            if isinstance(left_data, dict) and 'data' in left_data:
                left_transcript = left_data.get('data', {})
            else:
                left_transcript = left_data

            right_response = client.get(f"{settings.STORAGE_URL}/download/{right_transcript_path}")
            right_response.raise_for_status()
            right_result = right_response.json()
            # Handle nested data structure: data.data.data
            right_data = right_result.get('data', {})
            if isinstance(right_data, dict) and 'data' in right_data:
                right_transcript = right_data.get('data', {})
            else:
                right_transcript = right_data

            # Combine transcript texts and format with metadata for sentiment service
            combined_transcript = {
                "metadata": {
                    "ref-id": str(job_id),
                    "used-model": left_transcript.get('model', 'large-v3'),
                    "transcribed-at": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    "company-code": "AUTO",
                    "agent-name": "System",
                    "source-file": filename
                },
                "text": left_transcript.get('text', '') + ' ' + right_transcript.get('text', ''),
                "segments": left_transcript.get('segments', []) + right_transcript.get('segments', [])
            }

            # Create temporary files for the API call
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as context_file:
                context_file.write(f"Analyze sentiment regarding: {competitor_name}")
                context_file_path = context_file.name

            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as transcript_file:
                json.dump(combined_transcript, transcript_file, indent=2)
                transcript_file_path = transcript_file.name

            # Call sentiment analysis service
            sentiment_url = f"{settings.SENTIMENT_URL}/analyze/contextual/file"
            print(f"[DEBUG] Sending sentiment analysis request to: {sentiment_url}")
            print(f"[DEBUG] Competitor: {competitor_name}")
            print(f"[DEBUG] Transcript metadata: {combined_transcript.get('metadata', {})}")
            print(f"[DEBUG] Transcript text length: {len(combined_transcript.get('text', ''))}")
            print(f"[DEBUG] Transcript segments count: {len(combined_transcript.get('segments', []))}")

            with open(context_file_path, 'rb') as ctx_file, open(transcript_file_path, 'rb') as trans_file:
                files = {
                    'context': ('context.txt', ctx_file, 'text/plain'),
                    'transcript': ('transcript.json', trans_file, 'application/json')
                }

                sentiment_response = client.post(sentiment_url, files=files)

                print(f"[DEBUG] Sentiment API response status: {sentiment_response.status_code}")
                print(f"[DEBUG] Sentiment API response headers: {dict(sentiment_response.headers)}")

                sentiment_response.raise_for_status()
                result = sentiment_response.json()

                print(f"[DEBUG] Sentiment API response: {json.dumps(result, indent=2)[:500]}")

                # Handle array response format (empty array returns no results)
                if isinstance(result, list):
                    if len(result) > 0:
                        sentiment_result = result[0]
                    else:
                        # Empty array - no sentiment detected
                        sentiment_result = {
                            "competitor": competitor_name,
                            "overall_sentiment": "neutral",
                            "message": "No sentiment analysis results returned"
                        }
                else:
                    sentiment_result = result

            # Clean up temporary files
            os.unlink(context_file_path)
            os.unlink(transcript_file_path)

        # Save sentiment result to database
        crud.create_sentiment_result(
            db,
            UUID(job_id),
            competitor_name,
            sentiment_result
        )

        return sentiment_result

    except Exception as e:
        db.close()
        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            # Log error but don't fail the entire job
            print(f"Sentiment analysis failed for {competitor_name} after 3 retries: {str(e)}")
            # Save error result
            error_result = {
                "error": str(e),
                "competitor": competitor_name,
                "overall_sentiment": "error"
            }
            crud.create_sentiment_result(
                db,
                UUID(job_id),
                competitor_name,
                error_result
            )
            return error_result
    finally:
        db.close()


@celery_app.task
def finalize_job(job_id: str, sentiment_results):
    """
    Finalize job processing and update status to COMPLETED.

    Args:
        job_id: UUID of the job
        sentiment_results: Results from all sentiment analysis tasks
    """
    db = SessionLocal()

    try:
        # Update job status to completed
        crud.update_job_status(db, UUID(job_id), models.JobStatus.COMPLETED)

        print(f"Job {job_id} completed successfully with {len(sentiment_results)} sentiment analyses")

    except Exception as e:
        # Get job details for notification
        job = crud.get_job(db, UUID(job_id))
        error_msg = f"Finalization failed: {str(e)}"

        # If finalization fails, mark as failed
        crud.update_job_status(
            db,
            UUID(job_id),
            models.JobStatus.FAILED,
            error_message=error_msg
        )

        # Send notification
        if job:
            send_notification(job_id, job.filename, error_msg, "finalize_job")

        raise
    finally:
        db.close()


@celery_app.task
def process_audio_pipeline(job_id: str):
    """
    Main task that orchestrates the entire audio processing pipeline.

    Pipeline:
    1. Transcribe left and right channels (parallel)
    2. Analyze for competitors
    3. Run sentiment analysis for each competitor (parallel)
    4. Finalize job
    """
    db = SessionLocal()

    try:
        # Get job details
        job = crud.get_job(db, UUID(job_id))
        if not job:
            raise Exception(f"Job {job_id} not found")

        # Build the task chain
        # Step 1: Transcribe both channels in parallel
        transcription_group = group(
            transcribe_audio_channel.s(job_id, job.left_channel_url, 'left'),
            transcribe_audio_channel.s(job_id, job.right_channel_url, 'right')
        )

        # Step 2: After both transcriptions complete, analyze competitors
        # Step 3: For each competitor, run sentiment analysis in parallel
        # Step 4: Finalize the job

        # Create the workflow
        workflow = chain(
            transcription_group,
            process_transcriptions.s(job_id)
        )

        # Execute the workflow
        workflow.apply_async()

    except Exception as e:
        # Get job details for notification
        job = crud.get_job(db, UUID(job_id))
        error_msg = f"Pipeline initialization failed: {str(e)}"

        crud.update_job_status(
            db,
            UUID(job_id),
            models.JobStatus.FAILED,
            error_message=error_msg
        )

        # Send notification
        if job:
            send_notification(job_id, job.filename, error_msg, "process_audio_pipeline")

        raise
    finally:
        db.close()


@celery_app.task
def process_transcriptions(transcript_paths, job_id: str):
    """
    Process transcriptions after both channels are transcribed.
    This task coordinates competitor analysis and sentiment analysis using Celery chains.
    """
    db = SessionLocal()
    try:
        # Get the transcript paths
        left_path = transcript_paths[0]
        right_path = transcript_paths[1]

        # Get the original filename from the job
        job = crud.get_job(db, UUID(job_id))
        filename = job.filename if job else "unknown"

        # Chain: analyze competitors -> process each competitor -> finalize
        workflow = chain(
            analyze_competitors.s(job_id, left_path, right_path),
            process_sentiment_analysis.s(job_id, left_path, right_path, filename)
        )

        workflow.apply_async()

    except Exception as e:
        try:
            # Get job details for notification
            job = crud.get_job(db, UUID(job_id))
            error_msg = f"Post-transcription processing failed: {str(e)}"

            crud.update_job_status(
                db,
                UUID(job_id),
                models.JobStatus.FAILED,
                error_message=error_msg
            )

            # Send notification
            if job:
                send_notification(job_id, job.filename, error_msg, "process_transcriptions")

            raise
        finally:
            db.close()


@celery_app.task
def process_sentiment_analysis(competitors_found, job_id: str, left_path: str, right_path: str, filename: str):
    """
    Process sentiment analysis for each competitor sequentially.
    This task is called after competitor analysis completes.
    """
    db = SessionLocal()

    try:
        if competitors_found and len(competitors_found) > 0:
            # Create a chain of sentiment analysis tasks (sequential processing)
            # This prevents server overload from simultaneous sentiment API calls
            sentiment_tasks = []
            for competitor in competitors_found:
                sentiment_tasks.append(
                    analyze_sentiment_for_competitor.s(job_id, competitor, left_path, right_path, filename)
                )

            # Chain all sentiment tasks together, then finalize
            workflow = chain(*sentiment_tasks, finalize_job.s(job_id))
            workflow.apply_async()
        else:
            # No competitors found, just finalize
            finalize_job.apply_async(args=[job_id, []])

    except Exception as e:
        # Get job details for notification
        job = crud.get_job(db, UUID(job_id))
        error_msg = f"Sentiment processing coordination failed: {str(e)}"

        crud.update_job_status(
            db,
            UUID(job_id),
            models.JobStatus.FAILED,
            error_message=error_msg
        )

        # Send notification
        if job:
            send_notification(job_id, job.filename, error_msg, "process_sentiment_analysis")

        raise
    finally:
        db.close()
