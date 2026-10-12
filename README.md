# TestCase Generation Platform - Local Setup

Run the platform locally with Docker and Python. This folder is the public on-prem package. It contains no provider keys. Copy `env.example` to `.env` and fill in your own values.

## Prerequisites

- Docker Desktop running
- Docker Compose available
- Python 3 installed

## Architecture (x86 vs arm)

- `x86_64` / `amd64` -> `docker-compose_cpu_standalone_x86.yml`
- `arm64` / Apple Silicon -> `docker-compose_cpu_standalone_arm.yml`

Images are pulled as `aiqualitica/aiqualitica:<service>-x86` or `-arm`. There is no vLLM container and no QClara service.

## Environment

```bash
cp env.example .env
```

`.env` is gitignored. Do not commit it.

| Type | Variable | Notes |
|------|----------|-------|
| Mandatory | `JWT_SECRET` | JWT signing secret. Generate with `openssl rand -base64 32`. Copy the same value into `config/gateway.yaml` `secret_key`. |
| Mandatory | `LLM_API_KEY` | API key for the chat provider. Any provider in the LiteLLM list below. |
| Optional | `MULTIMODAL_API_KEY` | API key for the multimodal provider. Leave empty to skip image and document understanding. |
| Optional | `LLM_TYPE` | Prompt family inside the app. It does not select the cloud provider. Default: `openai`. |
| Optional | `LITELLM_MASTER_KEY` | Bearer `llm-service` sends to LiteLLM. Default: `sk-litellm-local`. Change it before sharing the host. |
| Optional | `GOOGLE_CLIENT_ID` | Needed only if Google login is required. |
| Optional | `GOOGLE_CLIENT_SECRET` | Needed only if Google login is required. |
| Optional | `CONTEXTFORGE_ADMIN_EMAIL` | ContextForge admin login. Default: `admin@aiqualitica.local`. |
| Optional | `CONTEXTFORGE_ADMIN_PASSWORD` | ContextForge admin password. Default: `ChangeMe1!`. |
| Optional | `CONTEXTFORGE_JWT_SECRET_KEY` | Signs ContextForge API JWTs. Generate a local value. |
| Optional | `AUTH_ENCRYPTION_SECRET` | Encrypts MCP credentials in ContextForge. Generate a local value. |
| Optional | `CONTEXTFORGE_SERVICE_TOKEN` | ContextForge API token. Create it in the admin UI after first login. |
| Optional | `KEYCLOAK_ADMIN_USERNAME` | Keycloak admin user. Default: `admin`. |
| Optional | `KEYCLOAK_ADMIN_PASSWORD` | Keycloak admin password. Default: `admin`. |
| Optional | `KEYCLOAK_ADMIN_CLIENT_SECRET` | admin-cli secret. Leave empty for local. |

### LiteLLM

`LLM_API_KEY` and `MULTIMODAL_API_KEY` are provider keys. Either key can come from any provider LiteLLM supports. Set the model in `litellm/config.standalone.yaml` as `provider/model-id`. The app always calls the route names `chat-model` and `multimodal-model`.

LiteLLM stores its state in the Postgres database `litellm`, created by `scripts/create_litellm_db.py`.

Providers with a chat route, from the [LiteLLM provider docs](https://docs.litellm.ai/docs/providers):

AI/ML API, AI21, Aleph Alpha, Amazon Nova, Anthropic, Anyscale, Apertis AI, AWS Bedrock, AWS SageMaker, Azure AI Studio, Azure OpenAI, Baseten, Bytez, Cerebras, Chutes, Clarifai, Cloudflare Workers AI, Codestral, Cohere, CometAPI, CompactifAI, CoralBricks, Crusoe, Dashscope, Databricks, DataRobot, DeepInfra, Deepseek, Docker Model Runner, EmpirioLabs, Featherless AI, Fireworks AI, FriendliAI, Galadriel, Gemini (Google AI Studio), GitHub Copilot, GitHub Models, GMI Cloud, GradientAI, Groq, Helicone, Heroku, Hugging Face, Hyperbolic, IBM watsonx.ai, Inception, Lambda AI, Lemonade, Llamafile, LlamaGate, LM Studio, Meta Llama, MiniMax, Mistral AI, Moonshot AI, Morph, NanoGPT, Nebius AI Studio, NLP Cloud, Novita AI, Nscale, Nvidia NIM, Ollama, OpenAI, OpenRouter, Oracle Cloud Infrastructure, OVHcloud, Perplexity, Petals, Poe, Predibase, PublicAI, QwenCloud, RAGFlow, Replicate, SambaNova, SAP Generative AI Hub, Sarvam.ai, Scaleway, Snowflake Cortex, Together AI, Vercel AI Gateway, Vertex AI, vLLM, Volcano Engine, Voyage AI, Weights & Biases, xAI, Xiaomi MiMo, Xinference, Z.AI.

The same docs also cover speech, image, video, and vector-store providers.

## 1) Using setup script

macOS and Linux:

```bash
chmod +x setup_cluster.sh
./setup_cluster.sh
```

Windows (Command Prompt, from this folder):

```bat
setup_cluster.bat
```

Optional flags are the same on both:

```bash
./setup_cluster.sh --platform x86
./setup_cluster.sh --platform arm
./setup_cluster.sh --recreate
```

```bat
setup_cluster.bat --platform x86
setup_cluster.bat --platform arm
setup_cluster.bat --recreate
```

On Windows, `--platform` defaults from `PROCESSOR_ARCHITECTURE`: `AMD64` uses the x86 compose file, `ARM64` uses the arm compose file.

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
docker compose --env-file .env -f "$COMPOSE_FILE" pull
docker compose --env-file .env -f "$COMPOSE_FILE" up -d
```

3. Initialize database:

```bash
python3 -m venv venv
source venv/bin/activate
pip install psycopg2-binary
python3 init_versioning_db.py
python3 scripts/create_litellm_db.py
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

Admin login defaults are in `env.example` (`KEYCLOAK_ADMIN_USERNAME` / `KEYCLOAK_ADMIN_PASSWORD`).

If your realm name is different, replace `tenant-default` in the URLs above.

### Login session (JWT cookie)

IAM sets Keycloak `accessTokenLifespan` to **1800 seconds (30 min)** when it creates a tenant realm. That value drives the `aiq_session` cookie after login. Re-login once after realm create/update to pick up a new cookie.

### ContextForge

- Admin UI: `http://localhost:4444/admin`
- Login defaults are in `env.example` (`CONTEXTFORGE_ADMIN_EMAIL` / `CONTEXTFORGE_ADMIN_PASSWORD`).
- After login, create an API token and put it in `CONTEXTFORGE_SERVICE_TOKEN`.

### Nginx

`nginx.standalone.conf` is the standalone entrypoint. The UI is served at `/`. API calls go to `/api/`. WebSocket and SSE go to the MCP gateway.

## Useful Commands

- Open app: `http://localhost`
- LiteLLM: `http://localhost:4000`
- Stop cluster:

```bash
docker compose --env-file .env -f docker-compose_cpu_standalone_x86.yml down
# or
docker compose --env-file .env -f docker-compose_cpu_standalone_arm.yml down
```

- Check status: `docker compose --env-file .env -f "$COMPOSE_FILE" ps`
- View logs: `docker compose --env-file .env -f "$COMPOSE_FILE" logs [service-name]`

Host ports match the current standalone cluster: API gateway `8000`, IAM `8001`, document preprocessor `8002`, requirement `8003`, database `8004`, TCM `8005`, LLM `8006`, manager `8007`, events `8008`, automation `8010`.
