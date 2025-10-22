# Sentiment Analysis Frontend - PHP Version

This is the PHP + HTML implementation of the sentiment analysis frontend, replacing the previous Svelte-based version.

## Tech Stack

- **PHP 8.2** with Apache
- **HTML** with Pico CSS for styling
- **JavaScript** for AJAX polling and interactivity
- **Docker** for containerization

## Features

- **Audio File Upload**: Upload and process audio files for sentiment analysis
- **Job Management**: View and track job status with real-time polling
- **Analytics Dashboard**: View sentiment statistics with date filtering
- **Pattern Management**: Manage positive/negative sentiment patterns
- **Admin Panel**: View raw database tables and storage files

## Project Structure

```
frontend-php/
├── config/
│   └── config.php              # Application configuration
├── src/
│   ├── api/
│   │   └── ApiClient.php       # API communication client
│   └── includes/
│       ├── header.php          # Shared header/navigation
│       └── footer.php          # Shared footer
├── public/
│   ├── index.php               # Home page (upload + job list)
│   ├── job.php                 # Job details page
│   ├── analytics.php           # Analytics dashboard
│   ├── patterns.php            # Pattern management
│   └── admin.php               # Admin database viewer
├── Dockerfile                  # Docker build configuration
├── docker-compose.yml          # Docker Compose setup
└── README.md                   # This file
```

## Configuration

Environment variables can be set in `docker-compose.yml`:

- `API_URL`: Orchestrator API endpoint
  - When running in Docker: `http://orchestrator-api:8000` (internal Docker network)
  - When running standalone: `http://10.1.0.35:8100` (external access)
- `SENTIMENT_API_URL`: Sentiment analysis API endpoint
  - When running in Docker: `http://sentiment-api:8008` (internal Docker network)
  - When running standalone: `http://10.1.0.35:8008` (external access)
- `APP_ENV`: Application environment (`production` or `development`)

### API Connectivity

The PHP frontend connects to the backend services via the Docker internal network when running as part of the docker-compose stack. This provides:

- **Better Performance**: Internal network communication is faster
- **Security**: APIs don't need to be exposed externally
- **Reliability**: No dependency on external network configuration

The frontend accesses the same database and APIs as the Svelte frontend:
- **Database**: PostgreSQL via Orchestrator API
- **Jobs Data**: `/jobs` endpoints from Orchestrator
- **Analytics**: `/analytics/*` endpoints from Orchestrator
- **Sentiment Patterns**: `/patterns/*` endpoints from Sentiment API
- **Admin Data**: `/admin/*` endpoints from Orchestrator
- **File Storage**: MinIO via Storage API through Orchestrator

## Installation

### Using Docker (Recommended)

1. Build and start the container:
```bash
docker-compose up -d --build
```

2. Access the application at `http://localhost:3210`

### Manual Setup

1. Install PHP 8.2+ with Apache
2. Enable required PHP extensions: `curl`
3. Configure Apache DocumentRoot to point to `public/` directory
4. Update API URLs in `config/config.php`
5. Ensure Apache has write permissions to the application directory

## Usage

### API Connectivity Test (`/test-api.php`)
- **NEW**: Test page to verify API connectivity
- Shows connection status to all backend endpoints
- Displays response times and sample data
- Useful for debugging and verifying the setup

### Home Page (`/index.php`)
- Upload audio files for processing
- View list of recent jobs
- Jobs automatically refresh when in PENDING or PROCESSING status

### Job Details (`/job.php?id=<job_id>`)
- View detailed job information
- Real-time progress tracking with polling
- View sentiment analysis results grouped by competitor

### Analytics Dashboard (`/analytics.php`)
- View overall sentiment statistics
- Filter by date range (last 7/30/90/365 days or custom)
- View competitor-specific details and mentions

### Pattern Management (`/patterns.php`)
- Add/delete positive and negative sentiment patterns
- Bulk upload patterns from text
- Search and filter patterns
- Bulk delete selected patterns

### Admin Panel (`/admin.php`)
- View raw jobs table
- View sentiment results table
- Browse storage files
- Export data to JSON

## API Integration

The frontend communicates with two backend services:

1. **Orchestrator API** (`API_URL`): Main API for job management, analytics, and admin functions
2. **Sentiment API** (`SENTIMENT_API_URL`): API for managing sentiment patterns

All API calls are handled through the `ApiClient` class in `src/api/ApiClient.php`.

## Real-time Updates

The frontend uses JavaScript AJAX polling for real-time updates:

- **Home page**: Polls every 5 seconds when jobs are PENDING or PROCESSING
- **Job details**: Polls every 5 seconds when job status is PENDING or PROCESSING
- Polling automatically stops when all jobs are completed or failed

## File Upload Limits

Default upload limits are configured in the Dockerfile:

- `upload_max_filesize`: 500MB
- `post_max_size`: 500MB
- `max_execution_time`: 300 seconds
- `max_input_time`: 300 seconds

Adjust these values in the Dockerfile if needed for larger files.

## Development

To run in development mode with error reporting:

1. Set `APP_ENV=development` in `docker-compose.yml`
2. Rebuild the container: `docker-compose up -d --build`

## Migration from Svelte

This PHP version maintains feature parity with the original Svelte frontend:

- ✅ All pages and features implemented
- ✅ Real-time polling for job updates
- ✅ Date filtering and analytics
- ✅ Pattern management with bulk operations
- ✅ Admin panel with search and export
- ✅ Same API endpoints and data flow
- ✅ Same CSS styling (Pico CSS)

### Key Differences

- **Server-side rendering**: Pages are generated by PHP instead of client-side JavaScript
- **Form submissions**: Standard HTML forms with POST requests
- **JavaScript usage**: Limited to polling, search, and interactive features only
- **Routing**: Standard PHP pages instead of SvelteKit routing

## Troubleshooting

### Cannot connect to API

- Verify `API_URL` and `SENTIMENT_API_URL` are correct
- Ensure backend services are running and accessible
- Check Docker network configuration if using containers

### File upload fails

- Check upload size limits in `.htaccess` or `php.ini`
- Verify PHP has write permissions to temporary directory
- Check backend API for upload errors

### Page not found

- Ensure Apache DocumentRoot points to `public/` directory
- Verify `mod_rewrite` is enabled if using URL rewriting
- Check Apache error logs: `docker logs sentiment-frontend-php`

## License

Same license as the parent sentiment analysis project.
