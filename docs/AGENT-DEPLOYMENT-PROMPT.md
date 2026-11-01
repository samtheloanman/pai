# AI Agent Deployment Prompt & Dual Setup Guide (Docker & Bare-Metal)

This document contains:
1. **Part 1:** Ready-to-paste instruction prompt for an autonomous AI agent to inspect, verify, and deploy PAI via Docker.
2. **Part 2:** Complete step-by-step instructions to run PAI natively **without Docker** (bare-metal on Linux or macOS).

---

## Part 1: Autonomous AI Agent Deployment Prompt

Copy and paste the prompt below into any AI agent (Claude Code, Gemini CLI, Hermes, Codex, etc.) to have it inspect the host and spin up PAI:

```text
You are an autonomous systems engineering agent. Your task is to inspect the host machine, verify container runtime prerequisites, and deploy the PAI (Private AI) appliance stack.

Execute the following verification and deployment protocol:

### Step 1: Pre-Flight Environmental Audit
1. Check OS and architecture:
   - Run: uname -s && uname -m
2. Check if Docker and Docker Compose are installed and running:
   - Run: docker --version && docker compose version && docker ps
   - If the Docker daemon is not active, report the exact error and start it (e.g., via `open /Applications/Docker.app` on macOS or `sudo systemctl start docker` on Linux).
3. Check memory availability:
   - Verify that the system has at least 16 GB of RAM (minimum 8 GB for the 4B model).
4. Verify port availability:
   - Check that ports 8088 (App), 4000 (LiteLLM), 8000 (Speaches), and 8080 (llama.cpp) are not in use by conflicting processes:
     lsof -i :8088 -i :4000 -i :8000 -i :8080 || true

### Step 2: Deployment Configuration
1. Navigate to the PAI prototype directory:
   - cd ~/Code/pai/prototype
2. If `.env` does not exist:
   - Copy `.env.example` to `.env`
   - Generate a cryptographically secure 16-byte LiteLLM key:
     openssl rand -hex 16
   - Generate a cryptographically secure 32-byte SQLCipher vault key:
     openssl rand -hex 32
   - Inject both into `.env` (LITELLM_MASTER_KEY and PAI_VAULT_KEY).
3. Ensure ports bind strictly to 127.0.0.1 for local isolation.

### Step 3: Stack Deployment
1. Build and bring up the container stack:
   - docker compose --profile local up -d --build
2. Tail container startup logs:
   - docker compose --profile local ps
   - docker logs --tail 25 prototype-app-1
   - docker logs --tail 25 prototype-litellm-1

### Step 4: Health Check & Verification Gate
1. Poll the application readiness endpoint:
   - curl -s -f http://127.0.0.1:8088/api/interview
2. Verify that all 4 containers are in the 'Up' or 'running' state:
   - prototype-app-1 (FastAPI UI)
   - prototype-litellm-1 (Gateway)
   - prototype-speaches-1 (Whisper/Kokoro)
   - prototype-llm-1 (llama.cpp)
3. Report success in Caveman mode: Output the live URL (http://localhost:8088) and active container status.
```

---

## Part 2: Bare-Metal Deployment Guide (Running Without Docker)

For users or servers that do not run Docker (e.g. lightweight VPS, native Arch/Fedora/Debian/macOS setups), PAI can run entirely with native system packages and Python virtual environments.

### 1. System Dependencies

#### macOS (Homebrew):
```bash
brew install python@3.12 sqlcipher git curl cmake pkg-config
```

#### Ubuntu / Debian:
```bash
sudo apt update && sudo apt install -y \
    python3.12 python3.12-venv python3.12-dev \
    libsqlcipher-dev sqlcipher \
    build-essential cmake git curl
```

#### Fedora / CentOS:
```bash
sudo dnf install -y \
    python3.12 python3.12-devel \
    sqlcipher sqlcipher-devel \
    cmake gcc gcc-c++ git curl
```

---

### 2. Service 1: Local Model Inference (`llama.cpp`)

Download and compile `llama.cpp` natively:
```bash
git clone https://github.com/ggerganov/llama.cpp ~/llama.cpp
cd ~/llama.cpp
cmake -B build
cmake --build build --config Release -j $(nproc 2>/dev/null || sysctl -n hw.ncpu)

# Run llama-server with Qwen3-4B GGUF
./build/bin/llama-server \
    -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M \
    --host 127.0.0.1 \
    --port 8080 \
    -c 8192 \
    --jinja
```

---

### 3. Service 2: Local Speech Server (`speaches`)

Faster-whisper and Kokoro TTS in a native virtual environment:
```bash
python3.12 -m venv ~/speaches-env
source ~/speaches-env/bin/activate
pip install --upgrade pip
pip install speaches

# Launch speech daemon on port 8000
python -m uvicorn --factory speaches.main:create_app --host 127.0.0.1 --port 8000
```

---

### 4. Service 3: Model Gateway (`LiteLLM`)

Proxy providing OpenAI-compatible endpoints across local models:
```bash
python3.12 -m venv ~/litellm-env
source ~/litellm-env/bin/activate
pip install 'litellm[proxy]'

# Run proxy with local configuration
litellm --config ~/Code/pai/prototype/litellm.local.yaml --port 4000 --host 127.0.0.1
```

---

### 5. Service 4: The PAI Application (`FastAPI` + React)

```bash
cd ~/Code/pai/prototype/app
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Export local configuration
export DATA_DIR="$HOME/.local/share/pai"
export LITELLM_URL="http://127.0.0.1:4000"
export SPEACHES_URL="http://127.0.0.1:8000"
export PAI_VAULT_KEY="$(openssl rand -hex 32)"
mkdir -p "$DATA_DIR"

# Launch PAI UI & API server
uvicorn main:app --host 127.0.0.1 --port 8088
```

Open [http://localhost:8088](http://localhost:8088) in your browser. All speech, database encryption, and model inference run natively on the host processor.
