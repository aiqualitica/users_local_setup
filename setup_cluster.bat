@echo off
setlocal EnableExtensions EnableDelayedExpansion

rem TestCase Generation Platform - Windows setup
rem 1. Create a Python virtual environment
rem 2. Install required dependencies
rem 3. Start the Docker Compose cluster (x86 or arm compose file)
rem 4. Wait for services to be ready
rem 5. Initialize the database schema
rem 6. Display cluster status
rem
rem Usage: setup_cluster.bat [--platform x86^|arm] [--recreate]

cd /d "%~dp0"

echo TestCase Generation Platform - Complete Setup
echo ==================================================

set "ARCH_SUFFIX="
set "RECREATE_DB=false"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="--help" goto show_help
if /I "%~1"=="-h" goto show_help
if /I "%~1"=="/?" goto show_help
if /I "%~1"=="--recreate" (
  set "RECREATE_DB=true"
  goto shift_one
)
if /I "%~1"=="--platform" goto parse_platform
echo [ERROR] Unknown option: %~1
echo Run setup_cluster.bat --help for usage.
exit /b 1

:parse_platform
if /I "%~2"=="x86" (
  set "ARCH_SUFFIX=x86"
  goto shift_two
)
if /I "%~2"=="arm" (
  set "ARCH_SUFFIX=arm"
  goto shift_two
)
echo [ERROR] Invalid platform: %~2 ^(expected x86 or arm^)
exit /b 1

:shift_one
shift
goto parse_args

:shift_two
shift
shift
goto parse_args

:args_done
if defined ARCH_SUFFIX goto platform_ready

if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "ARCH_SUFFIX=arm"
if /I "%PROCESSOR_ARCHITECTURE%"=="AMD64" set "ARCH_SUFFIX=x86"
if /I "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "ARCH_SUFFIX=arm"
if /I "%PROCESSOR_ARCHITEW6432%"=="AMD64" set "ARCH_SUFFIX=x86"

if not defined ARCH_SUFFIX (
  echo [ERROR] Unsupported architecture: %PROCESSOR_ARCHITECTURE%. Use --platform x86 or --platform arm.
  exit /b 1
)
echo [INFO] Auto-detected platform: %ARCH_SUFFIX%

:platform_ready
set "COMPOSE_FILE=docker-compose_cpu_standalone_%ARCH_SUFFIX%.yml"
if not exist "%COMPOSE_FILE%" (
  echo [ERROR] Compose file not found: %COMPOSE_FILE%
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Docker is not running. Please start Docker Desktop first.
  exit /b 1
)

set "COMPOSE="
docker compose version >nul 2>&1 && set "COMPOSE=docker compose"
if not defined COMPOSE (
  where docker-compose >nul 2>&1 && set "COMPOSE=docker-compose"
)
if not defined COMPOSE (
  echo [ERROR] Docker Compose is not installed.
  exit /b 1
)

echo [INFO] Using compose file: %COMPOSE_FILE%
echo [INFO] Starting setup process...

echo [INFO] Step 1: Setting up Python virtual environment...
set "PYTHON="
py -3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=py -3"
  goto python_ready
)
python -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=python"
  goto python_ready
)
python3 -c "import sys" >nul 2>&1
if not errorlevel 1 (
  set "PYTHON=python3"
  goto python_ready
)
echo [ERROR] Python 3 was not found. Install Python 3 and retry.
exit /b 1

:python_ready

if not exist "venv\Scripts\python.exe" (
  %PYTHON% -m venv venv
  if errorlevel 1 (
    echo [ERROR] Failed to create the Python virtual environment.
    exit /b 1
  )
  echo [OK] Created Python virtual environment
) else (
  echo [WARN] Virtual environment already exists, skipping creation
)

echo [INFO] Step 2: Activating virtual environment...
call "venv\Scripts\activate.bat"
if errorlevel 1 (
  echo [ERROR] Failed to activate the virtual environment.
  exit /b 1
)
echo [OK] Virtual environment activated

echo [INFO] Step 3: Installing Python dependencies...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip.
  exit /b 1
)
python -m pip install psycopg2-binary
if errorlevel 1 (
  echo [ERROR] Failed to install Python dependencies.
  exit /b 1
)
echo [OK] Python dependencies installed

echo [INFO] Step 4: Starting Docker Compose cluster...
%COMPOSE% -f "%COMPOSE_FILE%" up -d
if errorlevel 1 (
  echo [ERROR] Docker Compose failed to start the cluster.
  exit /b 1
)
echo [OK] Docker Compose cluster started

echo [INFO] Step 5: Waiting for PostgreSQL to be ready...
set "attempt=1"

:wait_postgres
if !attempt! GTR 30 goto postgres_timeout
%COMPOSE% -f "%COMPOSE_FILE%" exec -T postgres pg_isready -U postgres >nul 2>&1
if not errorlevel 1 goto postgres_ready
echo [INFO] Waiting for PostgreSQL... ^(attempt !attempt!/30^)
ping -n 3 127.0.0.1 >nul
set /a attempt+=1
goto wait_postgres

:postgres_timeout
echo [ERROR] PostgreSQL failed to start within expected time
exit /b 1

:postgres_ready
echo [OK] PostgreSQL is ready!

echo [INFO] Step 6: Waiting for database to be accessible...
ping -n 6 127.0.0.1 >nul

echo [INFO] Step 7: Initializing database schema...
set "DB_HOST=localhost"
set "DB_PORT=5432"
set "DB_NAME=testcase_db"
set "DB_USER=postgres"
set "DB_PASSWORD=password"

if /I "!RECREATE_DB!"=="true" (
  echo [WARN] Recreating database schema ^(all testcase_db data will be deleted^)...
  python init_versioning_db.py --recreate
) else (
  python init_versioning_db.py
)
if errorlevel 1 (
  echo [ERROR] Database initialization failed
  exit /b 1
)
echo [OK] Database initialization completed successfully!

echo [INFO] Creating LiteLLM database if it is missing...
python scripts\create_litellm_db.py
if errorlevel 1 (
  echo [ERROR] LiteLLM database creation failed
  exit /b 1
)

echo [INFO] Step 8: Checking cluster status...
echo.
echo Setup Complete! Cluster Status:
echo ==================================
%COMPOSE% -f "%COMPOSE_FILE%" ps

echo.
echo [INFO] Access your application at: http://localhost
echo [INFO] Keycloak Admin: http://localhost:8090
echo [INFO] RabbitMQ Management: http://localhost:15672
echo [INFO] Neo4j Browser: http://localhost:7474
echo [INFO] Weaviate: http://localhost:8082
echo.
echo [OK] Setup completed successfully!
echo [INFO] To stop the cluster later, run: %COMPOSE% -f %COMPOSE_FILE% down
echo [INFO] To reactivate the environment, run: venv\Scripts\activate.bat
exit /b 0

:show_help
echo Usage: setup_cluster.bat [--platform x86^|arm] [--recreate]
echo   x86  Intel/AMD64 ^(docker-compose_cpu_standalone_x86.yml^)
echo   arm  ARM64, including Windows on ARM ^(docker-compose_cpu_standalone_arm.yml^)
echo   --recreate  Drop and recreate testcase_db schema ^(destructive^)
echo If --platform is omitted, architecture is auto-detected from PROCESSOR_ARCHITECTURE.
exit /b 0
