# backend

A FastAPI application: backend

## Setup

### Prerequisites

- Python 3.11 or higher
- pip or poetry for package management

### Installation

1. Clone the repository (or navigate to your project directory)

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env and update with your configuration
```

### Environment Variables

#### Sentry Error Monitoring (Optional)

Sentry integration is **optional** and disabled by default. To enable:

```bash
# Enable Sentry
SENTRY_ENABLED=true

# Required: Your Sentry DSN (get it from Sentry dashboard)
SENTRY_DSN=https://your-key@your-org.ingest.sentry.io/project-id

# Optional: Environment name (defaults to APP_ENVIRONMENT)
SENTRY_ENVIRONMENT=production

# Optional: Release version (defaults to APP_VERSION)
SENTRY_RELEASE=v2.11.0

# Optional: Performance monitoring sample rate (0.0-1.0, default: 1.0)
# Use lower values (e.g., 0.1) in production to reduce overhead
SENTRY_TRACES_SAMPLE_RATE=1.0

# Optional: Profiling sample rate (0.0-1.0, default: 1.0)
SENTRY_PROFILES_SAMPLE_RATE=1.0
```

**Note:** If `SENTRY_ENABLED=false` or `SENTRY_DSN` is not set, Sentry will not be initialized and the application will run normally without error monitoring.

5. Initialize the database:
```bash
# Run migrations if using Alembic
alembic upgrade head

# Or for simple setup with SQLite (tables will be created automatically on first run)
```

### Running the Application

Development mode with auto-reload:
```bash
uvicorn main:app --reload
```

Or:
```bash
python main.py
```

The API will be available at:
- Main API: http://localhost:8000
- Interactive docs (Swagger): http://localhost:8000/docs
- Alternative docs (ReDoc): http://localhost:8000/redoc

## Project Structure

```
.
├── main.py                 # Application entry point
├── app/
│   ├── __init__.py
│   ├── core/              # Core utilities
│   │   ├── config.py      # Configuration management
│   │   ├── database.py    # Database setup
│   │   └── __init__.py
│   └── modules/           # Feature modules
│       └── __init__.py
├── requirements.txt       # Python dependencies
├── .env                  # Environment variables (not in git)
├── .gitignore
├── .flake8               # Flake8 linter configuration
├── .pylintrc             # Pylint configuration
├── pyproject.toml        # Project metadata and tool configuration
└── README.md
```

## Adding Modules

This project uses `fastapi-blocks-registry` for modular architecture. To add pre-built modules:

```bash
# List available modules
fastapi-registry list

# Add a module (e.g., auth)
fastapi-registry add auth

# Get module information
fastapi-registry info auth
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black .
```

### Linting

```bash
ruff check .
```

## Environment Variables

Key environment variables (see `.env` file):

- `PROJECT_NAME`: Application name
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: Secret key for security (change in production!)
- `CORS_ORIGINS`: Allowed CORS origins (JSON array format: `["http://localhost:3000","http://localhost:5173"]`)
- `CORS_METHODS`: Allowed HTTP methods (JSON array format: `["GET","POST"]` or `["*"]` for all)
- `CORS_HEADERS`: Allowed HTTP headers (JSON array format: `["*"]` for all)
- `ENVIRONMENT`: Environment (development/production)

### Storage Configuration

- `STORAGE_TYPE`: Storage backend type (`local` or `s3`, default: `local`)
- `STORAGE_BASE_URL`: Base URL for serving uploaded files (e.g., `http://localhost:8000`)
- `STORAGE_LOCAL_PATH`: Local storage base path (default: `./uploads`)
- `STORAGE_MAX_FILE_SIZE`: Maximum file size in bytes for regular users (default: `20971520` = 20 MB)
- `STORAGE_MAX_FILE_SIZE_ADMIN`: Maximum file size in bytes for administrators (default: `52428800` = 50 MB)
- `STORAGE_MAX_FILES_PER_ITEM`: Maximum number of images per item (default: `10`)
- `STORAGE_ALLOWED_MIME_TYPES`: Allowed MIME types (JSON array format: `["image/jpeg","image/png","image/webp","image/gif"]`)
- `STORAGE_ENABLE_PROCESSING`: Enable auto-resize and optimization (default: `true`)
- `STORAGE_MAX_WIDTH`: Maximum image width for processing (default: `1920`)
- `STORAGE_MAX_HEIGHT`: Maximum image height for processing (default: `1920`)
- `STORAGE_JPEG_QUALITY`: JPEG compression quality 1-100 (default: `85`)
- `STORAGE_CONVERT_TO_WEBP`: Convert images to WebP format (default: `false`)

**S3 Storage Configuration** (if `STORAGE_TYPE=s3`):
- `STORAGE_S3_BUCKET`: S3 bucket name
- `STORAGE_S3_ACCESS_KEY`: S3 access key ID
- `STORAGE_S3_SECRET_KEY`: S3 secret access key
- `STORAGE_S3_REGION`: S3 region (default: `us-east-1`)
- `STORAGE_S3_ENDPOINT_URL`: S3 endpoint URL (for S3-compatible services like MinIO). Used for internal operations (upload, download, delete).
- `STORAGE_S3_PUBLIC_ENDPOINT_URL`: Public S3 endpoint URL for generating accessible URLs (e.g., `http://localhost:9000` for MinIO in Docker). If not set, uses `STORAGE_S3_ENDPOINT_URL`. Useful when MinIO is in Docker and internal endpoint (`http://minio:9000`) is not accessible from browser.

### Email Configuration

The application supports two email adapters:

**1. File Adapter (Development - Default)**
- Emails are saved to files instead of being sent
- Useful for development and testing
- Default configuration:
  ```bash
  EMAIL_ENABLED=true
  EMAIL_ADAPTER=file
  EMAIL_FILE_PATH=./emails
  ```
- Emails are saved in `./emails/YYYY-MM-DD/` directory with HTML and JSON metadata

**2. SMTP Adapter (Production)**
- Sends emails via SMTP server
- Configuration:
  ```bash
  EMAIL_ENABLED=true
  EMAIL_ADAPTER=smtp
  SMTP_HOST=smtp.example.com
  SMTP_PORT=587
  SMTP_USER=your-email@example.com
  SMTP_PASSWORD=your-password
  SMTP_FROM=noreply@example.com
  SMTP_USE_TLS=true
  EMAIL_ENABLE_RETRY=false  # Enable retry with exponential backoff
  EMAIL_MAX_RETRIES=5       # Max retry attempts (if retry enabled)
  ```

**Email Audit Logging**
- Email audit logging to database (enabled by default):
  ```bash
  EMAIL_ENABLE_AUDIT=true
  ```
- Stores email metadata, templates, and context in database for audit trail

**Example SMTP Providers:**
- **Gmail**: `smtp.gmail.com:587` (requires app password)
- **SendGrid**: `smtp.sendgrid.net:587`
- **Mailgun**: `smtp.mailgun.org:587`
- **AWS SES**: `email-smtp.region.amazonaws.com:587`

## License

[Your License Here]

