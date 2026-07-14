# TestCase Generation Platform - Local Setup

Run the platform locally with Docker and Python.

## Prerequisites

- Docker Desktop running
- Docker Compose available
- Python 3 installed

## Architecture (x86 vs arm)

- `x86_64` / `amd64` -> `docker-compose_cpu_standalone_x86.yml`
- `arm64` / Apple Silicon -> `docker-compose_cpu_standalone_arm.yml`

## Environment Variables

Create `.env` from template:

```bash
cp env.template .env
```

| Type | Variable | Notes |
|------|----------|-------|
| Mandatory | `JWT_SECRET` | JWT signing secret (use a random value, e.g. `openssl rand -base64 32`). |
| Mandatory | `LLM_API_KEY` | API key for the selected cloud LLM provider (see below). |
| Optional | `LLM_TYPE` | Provider/model family. Default: `openai`. |
| Optional | `LLM_DEPLOYMENT_TYPE` | `api`, `togetherai`, `vllm`, or `local`. Default: `api`. |
| Optional | `LLM_MODEL_PATH` | Cloud model id or local model path. Default: `gpt-4.1`. |
| Optional | `GOOGLE_CLIENT_ID` | Needed only if Google login is required. |
| Optional | `GOOGLE_CLIENT_SECRET` | Needed only if Google login is required. |

Google keys are optional unless you explicitly enable Google login in Keycloak.

### LLM provider quick setup

Compose defaults to **OpenAI**. Switch provider by setting these in `.env`:

**OpenAI**
```bash
LLM_DEPLOYMENT_TYPE=api
LLM_TYPE=openai
LLM_MODEL_PATH=gpt-4.1
LLM_API_KEY=sk-...
```

**Anthropic (Claude)**
```bash
LLM_DEPLOYMENT_TYPE=api
LLM_TYPE=anthropic
LLM_MODEL_PATH=claude-sonnet-4-20250514
LLM_API_KEY=sk-ant-...
```

**Google Gemini**
```bash
LLM_DEPLOYMENT_TYPE=api
LLM_TYPE=gemini
LLM_MODEL_PATH=gemini-2.0-flash
LLM_API_KEY=your_gemini_api_key
```

**Together AI**
```bash
LLM_DEPLOYMENT_TYPE=togetherai
LLM_TYPE=deepseek_v3
LLM_MODEL_PATH=deepseek-ai/DeepSeek-V2.5
LLM_API_KEY=your_together_api_key
```

Full matrix (vLLM, local models, prompt builders, troubleshooting): see [`../llm-service/README.md`](../llm-service/README.md).

## 1) Using setup script

```bash
chmod +x setup_cluster.sh
./setup_cluster.sh
```

Optional flags:

```bash
./setup_cluster.sh --platform x86
./setup_cluster.sh --platform arm
./setup_cluster.sh --recreate
```

## 2) Step-by-step manual setup

1. Select compose file:

```bash
# x86
export COMPOSE_FILE=docker-compose_cpu_standalone_x86.yml

# arm
export COMPOSE_FILE=docker-compose_cpu_standalone_arm.yml
```

2. Start containers:

```bash
docker compose -f "$COMPOSE_FILE" pull
docker compose -f "$COMPOSE_FILE" up -d
```

3. Initialize database:

```bash
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary
python3 init_versioning_db.py
```

Use this only for a full DB reset:

```bash
python3 init_versioning_db.py --recreate
```

### Keycloak (default local setup)

- Master realm (Admin Console): `http://localhost:8090/admin/master/console/`
- Tenant realm (Admin Console, default `tenant-default`): `http://localhost:8090/admin/master/console/#/tenant-default`
- Tenant user (Account Console): `http://localhost:8090/realms/tenant-default/account`
- Tenant admin (Admin Console for tenant realm): `http://localhost:8090/admin/master/console/#/tenant-default`

If your realm name is different, replace `tenant-default` in the URLs above.

## Useful Commands

- Open app: `http://localhost`
- Stop cluster:

```bash
docker compose -f docker-compose_cpu_standalone_x86.yml down
# or
docker compose -f docker-compose_cpu_standalone_arm.yml down
```

- Check status: `docker compose -f "$COMPOSE_FILE" ps`
- View logs: `docker compose -f "$COMPOSE_FILE" logs [service-name]`
