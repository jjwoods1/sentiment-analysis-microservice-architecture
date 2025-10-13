# Quick Start Guide

Get the audio processing pipeline running in 5 minutes!

## Prerequisites

- Docker Desktop installed and running
- 4GB+ RAM available
- Access to external services (Auth, Split, Transcription, Sentiment APIs)

## Setup Steps

### 1. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials (use your preferred editor)
notepad .env  # Windows
# or
nano .env     # Linux/Mac
```

Required variables:
- `AUTH_URL`, `AUTH_USERNAME`, `AUTH_PASSWORD`: Your auth service credentials
- `SPLIT_URL`: Audio split service endpoint
- `TRANSCRIPTION_URL`: Transcription service endpoint
- `SENTIMENT_URL`: Sentiment analysis service endpoint
- `API_KEY`: Secure key for webhook endpoint (choose any secure string)
- `SMTP_USERNAME`, `SMTP_PASSWORD`: Your email credentials for Hostinger (smtp.hostinger.com:465)
- `NOTIFICATION_EMAILS`: Comma-separated list of email addresses to receive error notifications

### 2. Start All Services

```bash
# Build and start all containers
docker-compose up -d

# Wait for services to be ready (30-60 seconds)
docker-compose ps
```

You should see all services with status "Up".

### 3. Run Database Migrations

```bash
docker-compose exec orchestrator-api alembic upgrade head
```

### 4. Access the Application

Open your browser to: **http://localhost:3200**

## Test the System

1. **Upload a test audio file**:
   - Click "Choose File" and select an audio file
   - Click "Upload and Process"

2. **Monitor progress**:
   - You'll be redirected to the job detail page
   - Status updates automatically every 5 seconds
   - Watch as it progresses: PENDING → PROCESSING → COMPLETED

3. **View results**:
   - Once completed, see competitor mentions
   - Review sentiment analysis for each competitor

## Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f worker
docker-compose logs -f orchestrator-api
```

### Restart Services
```bash
docker-compose restart
```

### Stop All Services
```bash
docker-compose down
```

### Complete Reset (including data)
```bash
docker-compose down -v
docker-compose up -d
docker-compose exec orchestrator-api alembic upgrade head
```

## Service URLs

- **Frontend**: http://localhost:3200
- **Orchestrator API**: http://localhost:8100
- **Orchestrator Docs**: http://localhost:8100/docs
- **Storage API**: http://localhost:8002
- **Storage Docs**: http://localhost:8002/docs
- **Notification API**: http://localhost:8003
- **Notification Docs**: http://localhost:8003/docs
- **Analysis API**: http://localhost:8001
- **Analysis Docs**: http://localhost:8001/docs
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)
- **PostgreSQL**: localhost:5432 (audiouser/audiopass/audiodb)

## Test Notifications

Send a test notification to verify your email setup:

```bash
curl -X POST http://localhost:8003/notify/job-failed \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "test-123",
    "filename": "test.mp3",
    "error_message": "This is a test notification",
    "stack_trace": "No actual error - just testing!"
  }'
```

Check your email inbox!

## Troubleshooting

### Port Already in Use
If you get a "port already in use" error:
```bash
# Stop conflicting services or change ports in docker-compose.yml
```

### Services Not Starting
```bash
# Check logs for errors
docker-compose logs

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Worker Not Processing Jobs
```bash
# Check worker is running
docker-compose ps worker

# View worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker
```

## Next Steps

- Review the full [README.md](README.md) for detailed documentation
- Customize `analysis_service/competitors.txt` with your competitor list
- Explore the API documentation at http://localhost:8000/docs
- Check out the architecture and processing pipeline details

## Production Deployment

For production deployment:
1. Change all default passwords (PostgreSQL, MinIO, Redis)
2. Use strong, unique API keys
3. Enable HTTPS/TLS
4. Use managed services (RDS, ElastiCache, S3)
5. Implement monitoring and alerting
6. Set up regular backups

See the README.md for complete production considerations.
