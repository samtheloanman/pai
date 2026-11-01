# PAI prototype (Docker)

Runs the PAI software on a laptop or a cloud VM: setup interview, chat with local memory, editable rules, and voice in and out.

| Service | What | Image |
|---|---|---|
| `llm` | llama.cpp server with a GGUF model (local mode only) | `ghcr.io/ggml-org/llama.cpp:server` |
| `speaches` | Local speech-to-text (faster-whisper) and text-to-speech (Kokoro) | `ghcr.io/speaches-ai/speaches:latest-cpu` |
| `litellm` | One OpenAI-compatible address for chat, STT and TTS | `ghcr.io/berriai/litellm:main-stable` |
| `app` | PAI web app: FastAPI back end + React chat front end (assistant-ui, Geist font), SQLite in the `data` volume | built from `app/Dockerfile` (builds `web/` first) |

Prototype only: image tags are not pinned yet, no login on the app, no A/B updates.

## Run on a laptop (32-64 GB)

```bash
cp .env.example .env            # set LITELLM_MASTER_KEY; pick MODEL_HF
docker compose --profile local up -d --build
open http://localhost:8088
```

- 32-64 GB: set `MODEL_HF=unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M` (~18 GB download). Give Docker Desktop at least 24 GB of memory (Settings → Resources).
- 16 GB or a small Docker VM: keep the default `Qwen3-4B-Instruct-2507` (~2.5 GB).
- Docker on a Mac has no GPU access, so the model runs on the CPU. For full speed on Apple Silicon run `llama-server` natively and point `litellm.local.yaml` at `http://host.docker.internal:8080/v1`.
- The first start downloads the model and the two voice models; the first answer waits for that.

## Setup mode with OpenRouter (optional)

Uses a free OpenRouter model for chat so setup works before a local model is downloaded. **The interview answers leave the machine** and free models may log prompts. Voice stays local.

```bash
# in .env: OPENROUTER_API_KEY=..., LITELLM_CONFIG=litellm.openrouter.yaml
docker compose up -d --build     # no --profile local: llm is not started
```

Switch back by setting `LITELLM_CONFIG=litellm.local.yaml` and running with `--profile local`. Free model IDs change; check openrouter.ai/models with the "free" filter.

## Run on a cloud VM

Same commands on any Linux VM with Docker (8+ GB RAM for the 4B model, 32+ GB for 30B-A3B). The app binds to `127.0.0.1` only. Reach it with either:

```bash
ssh -L 8088:localhost:8088 user@vm
```

or by installing Tailscale on the VM and changing the port binding to the VM's Tailscale IP. Do not publish port 8088 on a public interface: the prototype has no login.

## Use it

1. **Setup**: answer 8 questions (type or tap Speak). Then "Draft my rules".
2. **Rules**: edit what PAI will and won't do. Saved on the box.
3. **Chat**: type, or tap the mic for a voice turn. Say "remember …" to store a memory.
4. **Memory**: see and forget anything PAI stored.

## Front end

`web/` is a Vite + React app using `@assistant-ui/react` for the chat screen. The Docker build compiles it into the Python app's static folder. Dev: `cd web && npm install && npm run dev` (proxies `/api` to :8088).

## Tests

```bash
cd app && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest && .venv/bin/pytest -q   # back end
cd ../web && npm test                                                                     # front end
```
