# Audio Processing Microservice Architecture

A production-ready, scalable audio processing pipeline with sentiment analysis, built using microservices architecture. This system processes audio call recordings, transcribes them, detects competitor mentions, and performs contextual sentiment analysis.

## Architecture Overview

The system consists of the following microservices:

- **Frontend Service**: SvelteKit web application with Pico.css styling
- **Orchestrator Service**: FastAPI-based API gateway and job orchestrator
- **Storage Service**: RESTful API for managing transcript storage in MinIO
- **Notification Service**: Multi-channel error notification system (Email, Webhook, Slack)
- **Analysis Service**: Competitor detection service
- **Worker Service**: Celery workers for background processing
- **PostgreSQL**: Relational database for job and result storage
- **Redis**: Message broker for Celery task queue
- **MinIO**: S3-compatible object storage for transcripts

## Features

- Audio file upload via web interface
- Real-time job status tracking with auto-polling
- Asynchronous background processing with Celery
- Automatic retry logic with exponential backoff (3 retries)
- **Multi-channel error notifications** (Email, Webhook, Slack)
- Competitor mention detection from transcripts
- Contextual sentiment analysis per competitor
- RESTful API with OpenAPI documentation
- Database migrations with Alembic
- Complete Docker containerization
- CORS-enabled for frontend integration

## Technology Stack

### Frontend
- **SvelteKit**: Modern web framework
- **Pico.css**: Minimal CSS framework for clean UI

### Backend
- **FastAPI**: High-performance Python web framework
- **SQLAlchemy**: ORM for database operations
- **Alembic**: Database migration tool
- **Celery**: Distributed task queue
- **Redis**: Message broker and result backend
- **Pydantic**: Data validation and settings management

### Storage
- **PostgreSQL 15**: Primary database
- **MinIO**: Object storage for transcripts

### Infrastructure
- **Docker & Docker Compose**: Containerization and orchestration

## Project Structure

```
.
├── docker-compose.yml          # Main orchestration file
├── .env.example               # Environment variables template
├── README.md                  # This file
│
├── frontend/                  # SvelteKit frontend
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +page.svelte              # Main upload & job list page
│   │   │   ├── +layout.svelte            # Layout with Pico.css
│   │   │   └── job/[id]/+page.svelte     # Job detail page
│   │   ├── lib/
│   │   │   └── api.js                    # API client functions
│   │   └── app.html                      # HTML template
│   ├── Dockerfile
│   ├── package.json
│   └── svelte.config.js
│
├── orchestrator/              # Main FastAPI orchestrator
│   ├── app/
│   │   ├── main.py           # FastAPI app with endpoints
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── schemas.py        # Pydantic schemas
│   │   ├── crud.py           # Database operations
│   │   ├── tasks.py          # Celery tasks
│   │   ├── celery_app.py     # Celery configuration
│   │   ├── config.py         # Settings management
│   │   ├── database.py       # Database setup
│   │   └── dependencies.py   # FastAPI dependencies
│   ├── alembic/              # Database migrations
│   │   ├── versions/
│   │   │   └── 001_initial_schema.py
│   │   ├── env.py
│   │   └── script.py.mako
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── analysis_service/          # Competitor analysis service
│   ├── app/
│   │   ├── main.py           # FastAPI app
│   │   ├── logic.py          # Competitor detection logic
│   │   └── config.py         # Settings
│   ├── competitors.txt        # List of competitors to detect
│   ├── Dockerfile
│   └── requirements.txt
│
├── storage_service/           # Storage service for transcripts
│   ├── app/
│   │   ├── main.py           # FastAPI app with REST endpoints
│   │   ├── storage.py        # MinIO storage manager
│   │   ├── schemas.py        # Pydantic schemas
│   │   └── config.py         # Settings
│   ├── Dockerfile
│   └── requirements.txt
│
└── notification_service/      # Notification service
    ├── app/
    │   ├── main.py           # FastAPI app with endpoints
    │   ├── notifiers.py      # Email, Webhook, Slack handlers
    │   ├── schemas.py        # Pydantic schemas
    │   └── config.py         # Settings
    ├── Dockerfile
    └── requirements.txt
```

## Setup Instructions

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB of available RAM
- Access to external services (Auth, Audio Split, Transcription, Sentiment)

### Step 1: Clone or Download the Project

```bash
cd sentiment-analysis-microservice-architecture
```

### Step 2: Configure Environment Variables

Copy the example environment file and configure with your credentials:

```bash
cp .env.example .env
```

Edit `.env` and fill in the required values:

```env
# External Service URLs
AUTH_URL=https://your-auth-service.com
AUTH_USERNAME=your-username
AUTH_PASSWORD=your-password
SPLIT_URL=https://your-audio-split-service.com
TRANSCRIPTION_URL=https://your-transcription-service.com
SENTIMENT_URL=https://your-sentiment-service.com

# API Security
API_KEY=your-secure-api-key-change-in-production
```

### Step 3: Customize Competitor List (Optional)

Edit `analysis_service/competitors.txt` to add or remove competitors to detect:

```txt
Amazon
Microsoft
Google
...
```

### Step 4: Build and Start Services

```bash
# Build all containers
docker-compose build

# Start all services
docker-compose up -d
```

This will start:
- Frontend at http://localhost:3200
- Orchestrator API at http://localhost:8100
- Analysis API at http://localhost:8001
- Storage API at http://localhost:8002
- Notification API at http://localhost:8003
- MinIO Console at http://localhost:9001
- PostgreSQL at localhost:5432

### Step 5: Run Database Migrations

```bash
docker-compose exec orchestrator-api alembic upgrade head
```

### Step 6: Verify Services

Check that all services are running:

```bash
docker-compose ps
```

All services should show status as "Up".

### Step 7: Access the Application

Open your browser and navigate to:
- **Frontend**: http://localhost:3200
- **Orchestrator API Docs**: http://localhost:8100/docs
- **Storage API Docs**: http://localhost:8002/docs
- **Notification API Docs**: http://localhost:8003/docs
- **Analysis API Docs**: http://localhost:8001/docs
- **MinIO Console**: http://localhost:9001 (login: minioadmin/minioadmin)

## Usage

### Uploading Audio Files

1. Navigate to http://localhost:3200
2. Click "Choose File" and select an audio file
3. Click "Upload and Process"
4. You'll be redirected to the job detail page

### Monitoring Job Progress

The job detail page automatically polls every 5 seconds for status updates. The pipeline progresses through these stages:

1. **PENDING**: Job created, waiting to start
2. **PROCESSING**: Audio is being split, transcribed, and analyzed
3. **COMPLETED**: All processing finished successfully
4. **FAILED**: An error occurred (error message displayed)

### Viewing Results

Once completed, the job detail page displays:
- Full job information
- List of competitors mentioned
- Sentiment analysis results for each competitor
- Complete JSON output from sentiment analysis

## API Endpoints

### Orchestrator API (Port 8000)

#### Upload Audio File
```http
POST /upload
Content-Type: multipart/form-data

file: <audio-file>
```

#### Webhook (Requires API Key)
```http
POST /webhook
X-API-KEY: your-api-key
Content-Type: application/json

{
  "filename": "call.mp3",
  "file_url": "https://example.com/audio.mp3"
}
```

#### Get All Jobs
```http
GET /jobs?skip=0&limit=100
```

#### Get Job Details
```http
GET /jobs/{job_id}
```

### Analysis API (Port 8001)

#### Find Competitors
```http
POST /find-competitors
Content-Type: application/json

{
  "transcript_text": "We discussed Amazon and Microsoft products..."
}
```

## Processing Pipeline

The complete audio processing pipeline works as follows:

1. **Upload & Split**:
   - User uploads audio file via frontend
   - Orchestrator creates job record in PostgreSQL
   - Audio is sent to external split service
   - Left and right channel URLs are stored

2. **Transcription** (Parallel):
   - Celery worker downloads both audio channels
   - Gets fresh auth token for each channel
   - Calls transcription service for each channel
   - Saves transcripts to Storage Service (which stores in MinIO)
   - Updates job with transcript paths

3. **Competitor Analysis**:
   - Downloads both transcripts from Storage Service
   - Combines transcript text
   - Calls analysis service to find competitors
   - Updates job with competitor list

4. **Sentiment Analysis** (Parallel):
   - For each competitor found
   - Creates context and transcript files
   - Calls sentiment service with context
   - Saves results to PostgreSQL

5. **Completion**:
   - Updates job status to COMPLETED
   - Frontend displays all results

## Error Handling

All external API calls include automatic retry logic:

- **Max Retries**: 3 attempts
- **Backoff Strategy**: Exponential (2^attempt seconds)
- **Failure Action**: Job marked as FAILED with error message
- **Partial Failures**: Sentiment analysis failures don't fail entire job

## Development

### Running Services Locally

To run individual services for development:

#### Orchestrator API
```bash
cd orchestrator
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Celery Worker
```bash
cd orchestrator
celery -A app.celery_app worker --loglevel=info
```

#### Analysis Service
```bash
cd analysis_service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Database Migrations

Create a new migration:
```bash
docker-compose exec orchestrator-api alembic revision -m "description"
```

Apply migrations:
```bash
docker-compose exec orchestrator-api alembic upgrade head
```

Rollback migration:
```bash
docker-compose exec orchestrator-api alembic downgrade -1
```

## Monitoring and Logs

### View Service Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator-api
docker-compose logs -f worker
docker-compose logs -f frontend
```

### Database Access

```bash
docker-compose exec postgres psql -U audiouser -d audiodb
```

### MinIO Access

Browse to http://localhost:9001 and login with:
- Username: `minioadmin`
- Password: `minioadmin`

### Redis Monitoring

```bash
docker-compose exec redis redis-cli
```

## Troubleshooting

### Services Won't Start

1. Check if ports are already in use:
   ```bash
   netstat -an | findstr "3000 8000 8001 5432 6379 9000"
   ```

2. Check service logs:
   ```bash
   docker-compose logs
   ```

3. Rebuild containers:
   ```bash
   docker-compose down -v
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Database Connection Issues

1. Ensure PostgreSQL is healthy:
   ```bash
   docker-compose ps postgres
   ```

2. Check database credentials in `.env`

3. Reset database:
   ```bash
   docker-compose down -v
   docker-compose up -d postgres
   docker-compose exec orchestrator-api alembic upgrade head
   ```

### Worker Not Processing Jobs

1. Check worker logs:
   ```bash
   docker-compose logs -f worker
   ```

2. Verify Redis connection:
   ```bash
   docker-compose exec redis redis-cli ping
   ```

3. Restart worker:
   ```bash
   docker-compose restart worker
   ```

### Frontend Not Loading

1. Check if backend API is accessible:
   ```bash
   curl http://localhost:8000/
   ```

2. Verify CORS settings in `orchestrator/app/main.py`

3. Check frontend logs:
   ```bash
   docker-compose logs -f frontend
   ```

## Production Considerations

### Security

- Change default passwords for PostgreSQL, MinIO, and Redis
- Use strong API keys
- Enable HTTPS/TLS for all services
- Implement rate limiting
- Add authentication/authorization to frontend
- Use secrets management (e.g., Docker Secrets, AWS Secrets Manager)
- Restrict CORS origins to specific domains

### Scalability

- Add more Celery workers:
  ```bash
  docker-compose up -d --scale worker=3
  ```

- Use managed services:
  - Amazon RDS for PostgreSQL
  - Amazon ElastiCache for Redis
  - Amazon S3 instead of MinIO

- Implement load balancing for API services

### Monitoring

- Add health check endpoints
- Implement logging aggregation (ELK stack, CloudWatch)
- Set up metrics collection (Prometheus, Grafana)
- Configure alerting for failures
- Monitor Celery task queue length

### Backup

- Regular PostgreSQL backups
- MinIO bucket replication
- Store environment files securely

## External Service Requirements

This system integrates with the following external services:

1. **Authentication Service**: Provides Bearer tokens for API access
2. **Audio Split Service**: Splits stereo audio into left/right channels
3. **Transcription Service**: Converts audio to text with timestamps
4. **Sentiment Analysis Service**: Analyzes sentiment with context

Ensure these services are accessible and properly configured.

## License

This project is provided as-is for production use.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review service logs
3. Verify external service connectivity
4. Check environment variable configuration
