# TestCase Generation Platform - Local Setup

This folder contains everything you need to run the TestCase Generation Platform locally.

## Files Included

- `docker-compose_cpu_standalone_x86.yml` - Compose for Intel/AMD64 (x86) images
- `docker-compose_cpu_standalone_arm.yml` - Compose for Apple Silicon / ARM64 images
- `nginx.standalone.conf` - Nginx configuration for reverse proxy
- `init_versioning_db.py` - Database initialization script
- `setup_cluster.sh` - Automated setup script (Linux/Mac)
- `env.template` - Environment variables template
- `README.md` - This documentation

## Choose the Right Compose File

Platform images are published per CPU architecture:

| Your machine | Compose file | Image tag suffix |
|--------------|--------------|------------------|
| Intel Mac, Linux amd64, Windows Docker (Intel) | `docker-compose_cpu_standalone_x86.yml` | `-x86` |
| Apple Silicon Mac, ARM Linux | `docker-compose_cpu_standalone_arm.yml` | `-arm` |

Example image: `aiqualitica/aiqualitica:testcase-manager-svc-x86`

## Quick Start

### Prerequisites

- Docker Desktop installed and running
- Docker Compose installed
- Python 3.x installed

### Required Setup (Before Running)

**1. Create `.env` file from template:**

```bash
cp env.template .env
```

**2. Edit the `.env` file and fill in these required variables:**

```env
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here
JWT_SECRET=your_jwt_secret_here
LLM_API_KEY=your_openai_api_key_here
```

**3. Get your credentials:**

- **Google OAuth:** [Google Cloud Console](https://console.cloud.google.com/) → Create OAuth 2.0 Client ID
- **OpenAI API:** [OpenAI Platform](https://platform.openai.com/) → Get API Key
- **JWT Secret:** Any secure string (e.g. `openssl rand -base64 32`)

### One-Command Setup

```bash
chmod +x setup_cluster.sh
./setup_cluster.sh
```

The script auto-detects your CPU architecture and selects the matching compose file. Override manually if needed:

```bash
./setup_cluster.sh --platform x86
./setup_cluster.sh --platform arm
```

This script will:

1. Create Python virtual environment
2. Install required dependencies
3. Start Docker Compose cluster
4. Wait for services to be ready
5. Initialize database schema
6. Display cluster status

## Access Points

After successful setup:

- **Main Application:** http://localhost
- **Keycloak Admin:** http://localhost:8090
- **RabbitMQ Management:** http://localhost:15672
- **Neo4j Browser:** http://localhost:7474
- **Weaviate:** http://localhost:8082

## Manual Setup (Alternative)

Set `COMPOSE_FILE` to the file matching your architecture:

```bash
# Intel / amd64
export COMPOSE_FILE=docker-compose_cpu_standalone_x86.yml

# Apple Silicon / arm64
export COMPOSE_FILE=docker-compose_cpu_standalone_arm.yml

docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d
```

### Initialize Database

```bash
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary
python3 init_versioning_db.py
```

## Stop the Cluster

```bash
docker compose -f docker-compose_cpu_standalone_x86.yml down
# or
docker compose -f docker-compose_cpu_standalone_arm.yml down
```

## Troubleshooting

### Check Service Status

```bash
docker compose -f docker-compose_cpu_standalone_x86.yml ps
```

### View Logs

```bash
docker compose -f docker-compose_cpu_standalone_x86.yml logs [service-name]
```

### Wrong Architecture / Image Pull Errors

If containers fail to start with platform errors, ensure you use the compose file matching your CPU:

- `x86_64` / `amd64` → `docker-compose_cpu_standalone_x86.yml`
- `aarch64` / `arm64` → `docker-compose_cpu_standalone_arm.yml`

### Environment Variables Issues

1. Check your `.env` file exists and has all required variables
2. Verify Google OAuth credentials are correct
3. Ensure OpenAI API key is valid
4. Check `JWT_SECRET` is set and matches `config/gateway.yaml` if you change it

## Services Included

- **PostgreSQL** (Port 5432) - Database
- **Redis** (Port 6379) - Caching
- **RabbitMQ** (Ports 5672, 15672) - Message Queue
- **Neo4j** (Ports 7474, 7687) - Graph Database
- **Weaviate** (Port 8082) - Vector Database
- **API Gateway** (Port 8000) - Main API
- **IAM Service** (Port 8001) - Authentication
- **LLM Service** (Port 8002) - AI/ML Processing
- **Nginx** (Ports 80, 443) - Reverse Proxy

## Building Images (Maintainers)

From `testcase-platform-deployment/scripts/`:

```bash
./build-all.sh --platform x86 --push --login
./build-all.sh --platform arm --push --login
```

Push existing local images without rebuilding:

```bash
./push-images.sh --platform x86 --login
```
