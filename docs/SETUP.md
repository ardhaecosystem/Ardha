# Ardha Setup Guide

## Overview

This guide provides comprehensive instructions for setting up Ardha in various environments, from local development to production deployment. Ardha uses a containerized architecture with Docker Compose for easy setup and management.

## Prerequisites

### System Requirements

**Minimum Requirements:**
- **RAM**: 8GB total (critical constraint)
- **CPU**: 4+ cores recommended
- **Disk**: 20GB free space
- **OS**: Linux, macOS, or Windows with WSL2

**Recommended Requirements:**
- **RAM**: 16GB for comfortable development
- **CPU**: 8+ cores
- **Disk**: 50GB SSD for better performance
- **Network**: Stable internet connection for AI services

### Required Software

**Essential:**
- [Docker](https://docs.docker.com/get-docker/) 24.0+
- [Docker Compose](https://docs.docker.com/compose/install/) 2.20+
- [Git](https://git-scm.com/) 2.40+

**Optional (for local development):**
- [Python](https://www.python.org/) 3.11+ (for backend development)
- [Node.js](https://nodejs.org/) 20.10+ LTS (for frontend development)
- [Poetry](https://python-poetry.org/) (Python dependency management)
- [pnpm](https://pnpm.io/) (Node.js package manager)

## Quick Start (5-Minute Setup)

### 1. Clone Repository

```bash
# Clone the repository
git clone https://github.com/ardhaecosystem/Ardha.git
cd Ardha

# Verify the repository structure
ls -la
```

### 2. Environment Configuration

```bash
# Copy environment template
cp backend/.env.example backend/.env

# Edit environment file (required for AI features)
nano backend/.env
```

**Minimum required configuration:**
```bash
# Database
DATABASE_URL=postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# Security
SECRET_KEY=your-very-secure-secret-key-here-change-this

# AI (required for AI features)
OPENROUTER_API_KEY=your-openrouter-api-key-here
AI_BUDGET_DAILY=2.0
AI_BUDGET_MONTHLY=60.0
```

### 3. Start Services

```bash
# Start all containers
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Initialize Database

```bash
# Run database migrations
docker-compose exec backend poetry run alembic upgrade head

# Create initial user (optional)
docker-compose exec backend poetry run python -m ardha.scripts.create_superuser
```

### 5. Verify Installation

```bash
# Check backend health
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs
```

**Services Available:**
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **Qdrant**: localhost:6333

## Detailed Setup

### Environment Configuration

#### Backend Environment Variables

Create `backend/.env` with the following configuration:

```bash
# =============================================================================
# Database Configuration
# =============================================================================
DATABASE_URL=postgresql+asyncpg://ardha_user:ardha_password@localhost:5432/ardha
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# =============================================================================
# Security Configuration
# =============================================================================
SECRET_KEY=your-very-secure-secret-key-here-change-this-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# =============================================================================
# AI Configuration
# =============================================================================
OPENROUTER_API_KEY=your-openrouter-api-key-here
AI_BUDGET_DAILY=2.0
AI_BUDGET_MONTHLY=60.0
DEFAULT_AI_MODEL=anthropic/claude-sonnet-4.5

# =============================================================================
# OAuth Configuration (Optional)
# =============================================================================
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# =============================================================================
# Email Configuration (Optional)
# =============================================================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@ardha.com

# =============================================================================
# Application Configuration
# =============================================================================
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# =============================================================================
# File Storage
# =============================================================================
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS=["pdf", "docx", "txt", "md", "py", "js", "ts", "json", "yaml"]
```

#### Frontend Environment Variables

Create `frontend/.env.local` for frontend configuration:

```bash
# =============================================================================
# API Configuration
# =============================================================================
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000

# =============================================================================
# Application Configuration
# =============================================================================
NEXT_PUBLIC_APP_NAME=Ardha
NEXT_PUBLIC_APP_VERSION=0.1.0
NEXT_PUBLIC_ENVIRONMENT=development

# =============================================================================
# Feature Flags
# =============================================================================
NEXT_PUBLIC_ENABLE_AI=true
NEXT_PUBLIC_ENABLE_GIT=true
NEXT_PUBLIC_ENABLE_NOTIFICATIONS=true

# =============================================================================
# Analytics (Optional)
# =============================================================================
NEXT_PUBLIC_ANALYTICS_ID=your-analytics-id
```

### Docker Compose Configuration

The `docker-compose.yml` file defines all services:

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: ardha-postgres
    environment:
      POSTGRES_DB: ardha
      POSTGRES_USER: ardha_user
      POSTGRES_PASSWORD: ardha_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    mem_limit: 2g
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ardha_user -d ardha"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Redis Cache
  redis:
    image: redis:7.2-alpine
    container_name: ardha-redis
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    mem_limit: 512m
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:v1.7.4
    container_name: ardha-qdrant
    environment:
      QDRANT__SERVICE__HTTP_PORT: 6333
      QDRANT__SERVICE__GRPC_PORT: 6334
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    mem_limit: 2.5g
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ardha-backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://ardha_user:ardha_password@postgres:5432/ardha
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
      - ./backend/.env:/app/.env
    ports:
      - "8000:8000"
    mem_limit: 2g
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Celery Worker
  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ardha-celery-worker
    command: celery -A ardha.core.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://ardha_user:ardha_password@postgres:5432/ardha
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./backend:/app
      - ./uploads:/app/uploads
      - ./backend/.env:/app/.env
    mem_limit: 1g
    depends_on:
      - postgres
      - redis
      - qdrant
    restart: unless-stopped

  # Celery Beat (Scheduler)
  celery-beat:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ardha-celery-beat
    command: celery -A ardha.core.celery beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://ardha_user:ardha_password@postgres:5432/ardha
      - REDIS_URL=redis://redis:6379
      - QDRANT_URL=http://qdrant:6333
    volumes:
      - ./backend:/app
      - ./backend/.env:/app/.env
      - celerybeat_data:/app/celerybeat-schedule
    mem_limit: 512m
    depends_on:
      - postgres
      - redis
      - qdrant
    restart: unless-stopped

  # Frontend (Next.js)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ardha-frontend
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    volumes:
      - ./frontend:/app
      - ./frontend/.env.local:/app/.env.local
    ports:
      - "3000:3000"
    mem_limit: 1g
    depends_on:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
  celerybeat_data:
```

### Database Setup

#### Initial Migration

```bash
# Enter backend container
docker-compose exec backend bash

# Run migrations
poetry run alembic upgrade head

# Verify migration status
poetry run alembic current

# View migration history
poetry run alembic history
```

#### Creating Superuser

```bash
# Create admin user
docker-compose exec backend poetry run python -m ardha.scripts.create_superuser

# Or manually create user via API
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "full_name": "Admin User",
    "password": "SecurePassword123"
  }'
```

#### Database Seeding (Optional)

```bash
# Seed with sample data
docker-compose exec backend poetry run python -m ardha.scripts.seed_data

# Seed AI models configuration
docker-compose exec backend poetry run python -m ardha.scripts.seed_ai_models
```

## Development Setup

### Backend Development

#### Local Development (without Docker)

```bash
# Navigate to backend directory
cd backend

# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Configure Poetry to use shared cache
poetry config cache-dir ../.poetry-cache

# Install dependencies
poetry install --no-root

# Activate virtual environment
poetry shell

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
poetry run alembic upgrade head

# Start development server
poetry run uvicorn ardha.main:app --reload --host 0.0.0.0 --port 8000
```

#### Backend Development Commands

```bash
# Start development server
poetry run uvicorn ardha.main:app --reload --port 8000

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=ardha --cov-report=html

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy .

# Linting
poetry run ruff check .
poetry run ruff check . --fix

# Database operations
poetry run alembic revision --autogenerate -m "description"
poetry run alembic upgrade head
poetry run alembic downgrade -1
```

### Frontend Development

#### Local Development (without Docker)

```bash
# Navigate to frontend directory
cd frontend

# Install pnpm (if not installed)
npm install -g pnpm

# Configure pnpm to use shared store
echo "store-dir=../.pnpm-store" > .npmrc

# Install dependencies
pnpm install

# Set up environment variables
cp .env.example .env.local
# Edit .env.local with your configuration

# Start development server
pnpm dev
```

#### Frontend Development Commands

```bash
# Start development server
pnpm dev

# Build for production
pnpm build

# Start production server
pnpm start

# Type checking
pnpm type-check

# Linting
pnpm lint
pnpm lint:fix

# Testing
pnpm test
pnpm test:coverage
pnpm test:e2e
```

## Production Setup

### Environment Preparation

#### Server Requirements

**Production Server Specifications:**
- **CPU**: 4+ cores (8+ recommended)
- **RAM**: 16GB+ (32GB+ recommended)
- **Storage**: 100GB+ SSD
- **Network**: 1Gbps+ connection
- **OS**: Ubuntu 20.04+ LTS or CentOS 8+

#### Security Configuration

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y docker.io docker-compose nginx certbot python3-certbot-nginx

# Add user to docker group
sudo usermod -aG docker $USER

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### Production Deployment

#### 1. Clone and Configure

```bash
# Clone repository
git clone https://github.com/ardhaecosystem/Ardha.git
cd Ardha

# Set up production environment
cp backend/.env.example backend/.env.production
cp frontend/.env.example frontend/.env.production
```

#### 2. Production Environment Configuration

**Backend (.env.production):**
```bash
# Production database (use managed database service)
DATABASE_URL=postgresql+asyncpg://user:pass@managed-db:5432/ardha_prod
REDIS_URL=redis://managed-redis:6379
QDRANT_URL=http://managed-qdrant:6333

# Security (generate strong secrets)
SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256

# AI configuration
OPENROUTER_API_KEY=your-production-openrouter-key
AI_BUDGET_DAILY=50.0
AI_BUDGET_MONTHLY=1500.0

# Production settings
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING

# CORS (update with your domain)
CORS_ORIGINS=["https://yourdomain.com"]

# Email configuration
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=noreply@yourdomain.com
```

**Frontend (.env.production):**
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com
NEXT_PUBLIC_APP_NAME=Ardha
NEXT_PUBLIC_ENVIRONMENT=production
```

#### 3. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ardha_prod
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always
    networks:
      - ardha-network

  redis:
    image: redis:7.2-alpine
    command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    restart: always
    networks:
      - ardha-network

  qdrant:
    image: qdrant/qdrant:v1.7.4
    volumes:
      - qdrant_data:/qdrant/storage
    restart: always
    networks:
      - ardha-network

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - QDRANT_URL=${QDRANT_URL}
    volumes:
      - ./uploads:/app/uploads
    restart: always
    networks:
      - ardha-network
    depends_on:
      - postgres
      - redis
      - qdrant

  celery-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    command: celery -A ardha.core.celery worker --loglevel=info
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - QDRANT_URL=${QDRANT_URL}
    volumes:
      - ./uploads:/app/uploads
    restart: always
    networks:
      - ardha-network
    depends_on:
      - postgres
      - redis
      - qdrant

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    restart: always
    networks:
      - ardha-network
    depends_on:
      - backend

networks:
  ardha-network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  qdrant_data:
```

#### 4. SSL Certificate Setup

```bash
# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d api.yourdomain.com

# Set up auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

#### 5. Nginx Configuration

Create `/etc/nginx/sites-available/ardha`:

```nginx
# Frontend (main domain)
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Backend API
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 6. Deploy Services

```bash
# Build and start production services
docker-compose -f docker-compose.prod.yml up -d --build

# Run database migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python -m ardha.scripts.create_superuser

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
```

## Monitoring and Maintenance

### Health Monitoring

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Check resource usage
docker stats

# Health check endpoints
curl https://api.yourdomain.com/health
```

### Backup Strategy

#### Database Backups

```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups"

# PostgreSQL backup
docker-compose exec -T postgres pg_dump -U ardha_user ardha > $BACKUP_DIR/postgres_$DATE.sql

# Qdrant backup
docker-compose exec -T qdrant curl -X POST http://localhost:6333/snapshots > $BACKUP_DIR/qdrant_$DATE.json

# Compress backups
tar -czf $BACKUP_DIR/ardha_backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
EOF

chmod +x backup.sh

# Set up cron job for daily backups
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

#### File Backups

```bash
# Backup uploaded files
rsync -av --delete ./uploads/ /backups/uploads/

# Backup configuration files
tar -czf /backups/config_$(date +%Y%m%d).tar.gz .env* docker-compose*.yml
```

### Log Management

```bash
# Configure log rotation
sudo cat > /etc/logrotate.d/ardha << 'EOF'
/path/to/ardha/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose restart backend
    endscript
}
EOF
```

## Troubleshooting

### Common Issues

#### Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U ardha_user

# View PostgreSQL logs
docker-compose logs postgres

# Reset database connection
docker-compose restart postgres
```

#### Redis Connection Issues

```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis

# Clear Redis cache
docker-compose exec redis redis-cli flushall
```

#### Qdrant Issues

```bash
# Check Qdrant status
curl http://localhost:6333/health

# View Qdrant logs
docker-compose logs qdrant

# Reset Qdrant data
docker-compose down
docker volume rm ardha_qdrant_data
docker-compose up -d
```

#### Backend Issues

```bash
# Check backend logs
docker-compose logs backend

# Restart backend service
docker-compose restart backend

# Enter backend container for debugging
docker-compose exec backend bash
```

#### Frontend Issues

```bash
# Check frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

### Performance Issues

#### Memory Optimization

```bash
# Check memory usage
docker stats

# Optimize PostgreSQL
# Edit postgresql.conf in container
docker-compose exec postgres nano /var/lib/postgresql/data/postgresql.conf

# Add optimizations:
shared_buffers = 512MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### Database Performance

```bash
# Analyze slow queries
docker-compose exec postgres psql -U ardha_user -d ardha -c "
SELECT query, mean_time, calls
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"

# Rebuild indexes
docker-compose exec postgres psql -U ardha_user -d ardha -c "REINDEX DATABASE ardha;"

# Update statistics
docker-compose exec postgres psql -U ardha_user -d ardha -c "ANALYZE;"
```

### Security Issues

#### SSL Certificate Problems

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate manually
sudo certbot renew

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

#### Access Control

```bash
# Check firewall status
sudo ufw status

# Review access logs
sudo tail -f /var/log/nginx/access.log

# Check failed login attempts
docker-compose logs backend | grep "authentication failed"
```

## Migration Guide

### From Development to Production

#### 1. Data Migration

```bash
# Export development data
docker-compose exec postgres pg_dump -U ardha_user ardha > dev_data.sql

# Import to production
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U ardha_user ardha_prod < dev_data.sql
```

#### 2. Configuration Migration

```bash
# Migrate environment variables
# Review and update all production settings
# Test with staging environment first
```

#### 3. Zero-Downtime Deployment

```bash
# Deploy new version
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d --no-deps backend
docker-compose -f docker-compose.prod.yml up -d --no-deps frontend

# Health check
curl https://api.yourdomain.com/health
```

## Advanced Configuration

### Custom Docker Images

#### Backend Dockerfile.prod

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only=main --no-dev

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 ardha && \
    chown -R ardha:ardha /app
USER ardha

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "ardha.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Frontend Dockerfile.prod

```dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile

# Build application
COPY . .
RUN pnpm build

# Production image
FROM node:20-alpine AS runner

WORKDIR /app

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Copy built application
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
```

### Environment-Specific Configurations

#### Staging Environment

```bash
# Create staging configuration
cp docker-compose.yml docker-compose.staging.yml
# Modify for staging-specific settings
```

#### Development Environment

```bash
# Create development overrides
cat > docker-compose.override.yml << 'EOF'
version: '3.8'

services:
  backend:
    volumes:
      - ./backend:/app
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  frontend:
    volumes:
      - ./frontend:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
EOF
```

---

## Support

### Documentation Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [Development Guide](DEVELOPMENT.md)
- [Testing Guide](TESTING.md)

### Community Support

- [GitHub Issues](https://github.com/ardhaecosystem/Ardha/issues)
- [GitHub Discussions](https://github.com/ardhaecosystem/Ardha/discussions)
- [Discord Community](https://discord.gg/ardha)

### Professional Support

For enterprise support and custom deployments, contact:
- Email: support@ardha.com
- Documentation: https://docs.ardha.com

---

**Version**: 1.0
**Last Updated**: November 24, 2024
**Maintained By**: Ardha Development Team
