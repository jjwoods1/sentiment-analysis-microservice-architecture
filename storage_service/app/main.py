from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional
import logging
from datetime import datetime

from . import schemas
from .storage import storage_manager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Storage Service API",
    description="Microservice for managing JSON transcript storage in MinIO",
    version="1.0.0"
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Storage Service",
        "bucket": storage_manager.client.bucket_exists(storage_manager.client._base_url.netloc)
    }


@app.post("/upload", response_model=schemas.UploadResponse)
async def upload_json(request: schemas.UploadRequest):
    """
    Upload JSON data to storage.

    - **object_path**: Path in storage (e.g., "transcripts/job-id/left.json")
    - **data**: JSON object to store
    """
    try:
        full_path = storage_manager.upload_json(request.object_path, request.data)
        return schemas.UploadResponse(
            success=True,
            object_path=request.object_path,
            full_path=full_path,
            message="JSON uploaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.get("/download/{object_path:path}", response_model=schemas.DownloadResponse)
async def download_json(object_path: str):
    """
    Download JSON data from storage.

    - **object_path**: Path in storage to download
    """
    try:
        data = storage_manager.download_json(object_path)
        if data is None:
            return schemas.DownloadResponse(
                success=False,
                object_path=object_path,
                data=None,
                message="Object not found"
            )

        return schemas.DownloadResponse(
            success=True,
            object_path=object_path,
            data=data,
            message="JSON downloaded successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.get("/presigned-url/{object_path:path}", response_model=schemas.PresignedUrlResponse)
async def get_presigned_url(
    object_path: str,
    expires: int = Query(3600, description="URL expiration in seconds", ge=60, le=604800)
):
    """
    Generate a presigned URL for direct download access.

    - **object_path**: Path in storage
    - **expires**: URL expiration time in seconds (60 to 604800, default 3600)
    """
    try:
        if not storage_manager.object_exists(object_path):
            raise HTTPException(status_code=404, detail="Object not found")

        url = storage_manager.get_presigned_url(object_path, expires)
        return schemas.PresignedUrlResponse(
            success=True,
            object_path=object_path,
            url=url,
            expires_in_seconds=expires
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate URL: {str(e)}")


@app.delete("/delete/{object_path:path}", response_model=schemas.DeleteResponse)
async def delete_object(object_path: str):
    """
    Delete an object from storage.

    - **object_path**: Path in storage to delete
    """
    try:
        success = storage_manager.delete_object(object_path)
        if not success:
            return schemas.DeleteResponse(
                success=False,
                object_path=object_path,
                message="Failed to delete object or object not found"
            )

        return schemas.DeleteResponse(
            success=True,
            object_path=object_path,
            message="Object deleted successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@app.get("/list", response_model=schemas.ListResponse)
async def list_objects(prefix: str = Query("", description="Filter by prefix")):
    """
    List objects in storage with optional prefix filter.

    - **prefix**: Optional prefix to filter objects (e.g., "transcripts/job-id/")
    """
    try:
        objects = storage_manager.list_objects(prefix)
        return schemas.ListResponse(
            success=True,
            prefix=prefix,
            objects=objects,
            count=len(objects)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List failed: {str(e)}")


@app.get("/exists/{object_path:path}", response_model=schemas.ExistsResponse)
async def check_exists(object_path: str):
    """
    Check if an object exists in storage.

    - **object_path**: Path in storage to check
    """
    try:
        exists = storage_manager.object_exists(object_path)
        return schemas.ExistsResponse(
            exists=exists,
            object_path=object_path
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")


@app.get("/health")
async def health_check():
    """
    Comprehensive health check including MinIO connectivity.
    """
    try:
        # Test MinIO connection
        bucket_exists = storage_manager.client.bucket_exists(storage_manager.settings.MINIO_BUCKET)

        logger.info("Health check: Storage service is healthy")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "storage-api",
            "minio_connected": True,
            "bucket_exists": bucket_exists,
            "bucket_name": storage_manager.settings.MINIO_BUCKET
        }
    except Exception as e:
        logger.error(f"Health check: Storage service is unhealthy - {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "storage-api",
                "minio_connected": False,
                "error": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
