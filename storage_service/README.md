# Storage Service

RESTful API microservice for managing JSON transcript storage in MinIO.

## Overview

The Storage Service provides a clean API layer over MinIO object storage, specifically designed for storing and retrieving audio transcription data. It abstracts MinIO operations and provides standardized endpoints for the orchestrator service.

## Features

- Upload JSON transcripts to MinIO
- Download transcripts by path
- Generate presigned URLs for direct downloads
- List objects by prefix
- Check object existence
- Delete objects
- Health checks with MinIO connectivity verification

## API Endpoints

### Upload JSON
```http
POST /upload
Content-Type: application/json

{
  "object_path": "transcripts/job-id/left.json",
  "data": { ... }
}
```

### Download JSON
```http
GET /download/{object_path}
```

### Generate Presigned URL
```http
GET /presigned-url/{object_path}?expires=3600
```

### List Objects
```http
GET /list?prefix=transcripts/job-id/
```

### Check Existence
```http
GET /exists/{object_path}
```

### Delete Object
```http
DELETE /delete/{object_path}
```

### Health Check
```http
GET /health
```

## Configuration

Environment variables:
- `MINIO_ENDPOINT`: MinIO server endpoint
- `MINIO_ACCESS_KEY`: MinIO access key
- `MINIO_SECRET_KEY`: MinIO secret key
- `MINIO_BUCKET`: Bucket name (default: audio-transcripts)
- `MINIO_SECURE`: Use HTTPS (default: false)

## Running Locally

```bash
cd storage_service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

## API Documentation

Once running, visit http://localhost:8002/docs for interactive API documentation.
