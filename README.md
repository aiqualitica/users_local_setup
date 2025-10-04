# TestCase Generation Platform - Local Setup

This folder contains everything you need to run the TestCase Generation Platform locally.

## 📁 Files Included

- `docker-compose_cpu_standalone.yml` - Docker Compose configuration for standalone deployment
- `docker-compose_cpu_standalone_windows.yml` - Windows-specific Docker Compose configuration
- `nginx.standalone.conf` - Nginx configuration for reverse proxy
- `init_versioning_db.py` - Database initialization script
- `setup_cluster.sh` - Automated setup script (Linux/Mac)
- `setup_cluster.bat` - Automated setup script (Windows)
- `env.template` - Environment variables template
- `README.md` - This documentation

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Docker Compose installed
- Python 3.x installed

### 🔐 Required Setup (Before Running)

**1. Create `.env` file from template:**
```bash
# Copy the environment template
cp env.template .env
```

**2. Edit the `.env` file and fill in these 4 required variables:**
```env
# Google OAuth (get from: https://console.cloud.google.com/)
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# JWT Secret (any string works)
JWT_SECRET=your_jwt_secret_here

# OpenAI API Key (get from: https://platform.openai.com/)
LLM_API_KEY=your_openai_api_key_here
```

**3. Get your credentials:**
- **Google OAuth:** [Google Cloud Console](https://console.cloud.google.com/) → Create OAuth 2.0 Client ID
- **OpenAI API:** [OpenAI Platform](https://platform.openai.com/) → Get API Key
- **JWT Secret:** Can be any string (e.g., "myapp123" or generate with `openssl rand -base64 32`)

### One-Command Setup

**For Linux/Mac:**
```bash
chmod +x setup_cluster.sh
./setup_cluster.sh
```

**For Windows:**
```cmd
setup_cluster.bat
```

**Note:** The `env.template` file contains all necessary configuration options with sensible defaults. You only need to configure the 4 mandatory fields for basic functionality.

This script will:
1. ✅ Create Python virtual environment
2. ✅ Install required dependencies
3. ✅ Start Docker Compose cluster
4. ✅ Wait for services to be ready
5. ✅ Initialize database schema
6. ✅ Display cluster status

## 🌐 Access Points

After successful setup:
- **Main Application:** http://localhost
- **RabbitMQ Management:** http://localhost:15672
- **Neo4j Browser:** http://localhost:7474
- **Qdrant Dashboard:** http://localhost:6333/dashboard

## 🛠️ Manual Setup (Alternative)

If you prefer to run commands manually:

### 1. Start the Cluster
```bash
docker-compose -f docker-compose_cpu_standalone.yml up -d
```

### 2. Wait for PostgreSQL
```bash
# Wait for PostgreSQL to be ready
docker-compose -f docker-compose_cpu_standalone.yml exec postgres pg_isready -U postgres
```

### 3. Initialize Database
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install psycopg2-binary

# Run database initialization
python3 init_versioning_db.py
```

## 🛑 Stop the Cluster

```bash
docker-compose -f docker-compose_cpu_standalone.yml down
```

## ⚙️ Advanced Configuration (Optional)

### Custom Environment Variables
You can customize these optional settings in your `.env` file:

```env
# Database Configuration (defaults work for local setup)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=testcase_db
DB_USER=postgres
DB_PASSWORD=password

# Custom Ports (optional)
TESTCASE_MANAGER_PORT=8000
API_LAYER_PORT=8001
LLM_SERVICE_PORT=8002
# ... other ports
```

### Custom Docker Compose Settings
- Edit `docker-compose_cpu_standalone.yml` for advanced Docker configurations
- Modify `nginx.standalone.conf` for custom Nginx settings
- Update `init_versioning_db.py` for database schema changes

## 🔧 Troubleshooting

### Check Service Status
```bash
docker-compose -f docker-compose_cpu_standalone.yml ps
```

### View Logs
```bash
docker-compose -f docker-compose_cpu_standalone.yml logs [service-name]
```

### Restart Services
```bash
docker-compose -f docker-compose_cpu_standalone.yml restart [service-name]
```

### Environment Variables Issues
If you see authentication errors:
1. **Check your `.env` file exists and has all required variables**
2. **Verify Google OAuth credentials are correct**
3. **Ensure OpenAI API key is valid and has credits**
4. **Check JWT_SECRET is set (can be any string)**

### Common Issues
- **"Authentication service unavailable"** → Check IAM service logs
- **"Google OAuth failed"** → Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET
- **"LLM service error"** → Check LLM_API_KEY and OpenAI account
- **"Database connection failed"** → Ensure PostgreSQL container is running

## 📊 Services Included

- **PostgreSQL** (Port 5432) - Database
- **Redis** (Port 6379) - Caching
- **RabbitMQ** (Ports 5672, 15672) - Message Queue
- **Neo4j** (Ports 7474, 7687) - Graph Database
- **Qdrant** (Port 6333) - Vector Database
- **API Gateway** (Port 8001) - Main API
- **IAM Service** (Port 8007) - Authentication
- **LLM Service** (Port 8002) - AI/ML Processing
- **Nginx** (Ports 80, 443) - Reverse Proxy

## 🎯 Features

- ✅ **Complete Test Case Management**
- ✅ **AI-Powered Test Case Generation**
- ✅ **TCM Integrations** (TestRail, Zephyr, Xray)
- ✅ **Subscription Management**
- ✅ **Multi-tenant Architecture**
- ✅ **Version Control**
- ✅ **Google OAuth Authentication**

## 📝 Notes

- The setup script automatically handles all dependencies
- Database is initialized with default subscription plans
- All services are configured for local development
- No external dependencies required (except Docker)

## 🆘 Support

If you encounter any issues:
1. Check that Docker Desktop is running
2. Verify all ports are available
3. Check service logs for specific errors
4. Ensure you have sufficient disk space (images are ~4GB total)
