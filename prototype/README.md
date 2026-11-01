# PAI prototype (Docker)

Runs the PAI software on a laptop or a cloud VM: setup interview, chat with local memory, editable rules, voice in and out, an approval gate for risky actions, an activity log, and opt-in cloud providers.

| Service | What | Image |
|---|---|---|
| `llm` | llama.cpp server with a GGUF model (local mode only) | `ghcr.io/ggml-org/llama.cpp:server` |
| `speaches` | Local speech-to-text (faster-whisper) and text-to-speech (Kokoro) | `ghcr.io/speaches-ai/speaches:latest-cpu` |
| `litellm` | One OpenAI-compatible address for chat, STT and TTS | `ghcr.io/berriai/litellm:main-stable` |
| `app` | PAI web app: FastAPI back end + React chat front end (assistant-ui, Geist font), encrypted SQLite (SQLCipher) vault in the `data` volume | built from `app/Dockerfile` (builds `web/` first) |

Prototype only: image tags are not pinned yet, no login on the app, no A/B updates. See Known limits.

## Run on a laptop (32-64 GB)

```bash
cp .env.example .env            # set LITELLM_MASTER_KEY and PAI_VAULT_KEY; pick MODEL_HF
docker compose --profile local up -d --build
open http://localhost:8088
```

- 32-64 GB: set `MODEL_HF=unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M` (~18 GB download). Give Docker Desktop at least 24 GB of memory (Settings → Resources).
- 16 GB or a small Docker VM: keep the default `Qwen3-4B-Instruct-2507` (~2.5 GB).
- Docker on a Mac has no GPU access, so the model runs on the CPU. For full speed on Apple Silicon run `llama-server` natively and point `litellm.local.yaml` at `http://host.docker.internal:8080/v1`.
- The first start downloads the model and the two voice models; the first answer waits for that.

## Vault key (required)

`PAI_VAULT_KEY` encrypts the vault (memories, rules, profile, pending actions). The app will not start without it. Generate one and put it in `.env`:

```bash
openssl rand -hex 32
```

**If you lose this key you lose the vault; there is no recovery.** Back it up somewhere other than this machine.

`AUDIT_CONTENT` (default `0`): the activity log stores metadata only (event kind, route, model name, durations, ids). Set `AUDIT_CONTENT=1` to also store message and memory text in the log.

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
5. **Approvals**: risky actions are proposed, never run directly. Saying "delete memory 3" in chat creates a pending action; it runs only when you press Confirm (at most once), and Reject or a timeout (15 minutes) discards it.
6. **Activity**: a hash-chained log of what PAI did (model calls, routes, proposals, confirmations, config changes). "Verify" re-checks the chain; it reports whether edits, deletions or reordering are detected.
7. **Providers**: optional cloud models, off by default. Add a provider key, turn cloud on, then tick the cloud toggle on a chat message to send that one message out. Cloud requests carry the message and recent chat only, never your profile, rules or memories, and messages that look like card numbers, government IDs or similar stay on the box. Provider keys and the cloud switch are written to files LiteLLM reads at start, so **restart the `litellm` container after changing providers** (`docker compose restart litellm`), then press "I restarted it" in Providers to clear the restart notice (`restart_required` is cleared by you, not detected).

## Routing and the route bench

Messages are routed by rules first, then embeddings, then a small decision model. Only a rule-matched message may write memory or propose an action; a model verdict never does. `bench/route_bench.py` posts labelled cases to `/api/route` (`python bench/route_bench.py --base http://localhost:8088`). **No accuracy or speed numbers have been measured yet.**

## Front end

`web/` is a Vite + React app using `@assistant-ui/react` for the chat screen. The Docker build compiles it into the Python app's static folder. Dev: `cd web && npm install && npm run dev` (proxies `/api` to :8088).

## Tests

```bash
cd app && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once
.venv/bin/pytest -q                                   # back end (e2e is skipped)
cd ../web && npm test                                 # front end
cd ../app && ./run-e2e.sh                             # end to end, see below
```

`run-e2e.sh` starts a throwaway fake LiteLLM (`tests/fake_litellm.py`) and uvicorn on temp directories with `PAI_EMBED=off` (skips the embedding model so nothing downloads), runs `tests/test_e2e.py` with `PAI_E2E=1`, then removes everything. It does not use Docker. It uses ports 4999 and 8099. To point the test at another server set `PAI_E2E_BASE` (and `PAI_E2E_FAKE`).

## Running a second copy

Compose names the project after the folder, so a second checkout can collide with a running stack. Use `docker compose -p <name> ...` and set a different `PAI_PORT` in `.env`.

## Known limits

- No login. Anyone who can reach the port can read memories and confirm actions: keep it on localhost or a private network.
- A provider key is stored in plaintext in the shared env file (mode 0600) that LiteLLM reads.
- The embedding model downloads on first use; until then (or if it fails) search uses keywords only.
- `restart_required` stays set until the owner clears it; the app cannot tell whether LiteLLM was restarted.
- Not built yet: OS image, Telegram/email channels, PII masking before cloud calls, learning beyond stored memories.
