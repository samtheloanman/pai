# PAI — Private AI Home Server

> **Your AI. Your house.**

PAI runs an AI assistant on your own computer: a local chat model, local speech-to-text and text-to-speech, an encrypted memory vault, an approval step for risky actions, and a tamper-evident activity log. Models and memory stay on the machine; cloud models are off unless you turn them on with your own key.

This repository is the open-source PAI software. It is a working prototype: there is no login yet and the PAI OS image is not built.

---

## How it works

```
 Browser (http://localhost:8088)  ·  voice  ·  CLI
                    │
                    ▼
 ┌─────────────────────────────────────────────────────────┐
 │ PAI app (FastAPI + React, port 8088)                    │
 │  setup interview · router · encrypted vault (SQLCipher) │
 │  approval gateway · append-only audit log               │
 └───────────────┬─────────────────────────┬───────────────┘
                 ▼                         ▼
 ┌───────────────────────────┐   ┌─────────────────────────┐
 │ LiteLLM gateway (4000)    │   │ Speaches voice (8000)   │
 │  pai-chat / pai-decide    │   │  faster-whisper (STT)   │
 └───────┬───────────────┬───┘   │  Kokoro (TTS)           │
         ▼               ▼       └─────────────────────────┘
  llama.cpp (8080)   optional cloud model
  local GGUF model   (your key, off by default)
```

| Piece | What it does |
|---|---|
| `llm` | llama.cpp server running a local GGUF model from Hugging Face. |
| `litellm` | One OpenAI-style API in front of every model. The app asks for `pai-chat`, `pai-decide`, `pai-stt`, `pai-tts`; LiteLLM maps them to real models. |
| `speaches` | Local voice: faster-whisper for speech-to-text, Kokoro for text-to-speech. |
| `app` | The PAI server and web UI: setup interview, memory vault, approvals, audit log. |

---

## Install

The full, step-by-step guide (also written so an AI coding agent can follow it) is **[INSTALL.md](INSTALL.md)**. Short version:

```bash
git clone https://github.com/samtheloanman/pai.git ~/pai
cd ~/pai/prototype
cp .env.example .env        # then create the vault key as INSTALL.md step 4 shows
scripts/pai-up --profile local up -d --build
```

Open **http://localhost:8088** and complete the setup interview. Check health with:

```bash
curl -fsS http://127.0.0.1:8088/api/health
```

Requirements: macOS or Linux (Windows only inside WSL2, untested), Docker with Compose v2, about 15 GB free disk, and 16 GB RAM for the default model.

**Quick demo instead:** `./run.sh` in the repo root starts a lighter stack on Ollama with `gemma3:4b`. It skips the vault-key setup in INSTALL.md, so use it only to try PAI out.

Never run `docker compose down -v` or delete `~/.config/pai` unless you mean to destroy the vault: there is no recovery without the key.

---

## Choosing a model

Set the model in `prototype/.env` with `MODEL_HF` (a Hugging Face `repo:quant` that llama.cpp downloads on first start), then restart with `scripts/pai-up --profile local up -d`.

| Your machine | Model | `MODEL_HF` | Download |
|---|---|---|---|
| 16 GB RAM (default) | Qwen3-4B Instruct | `unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M` | about 2.5 GB |
| 32–64 GB RAM | Qwen3-30B-A3B Instruct (mixture of experts) | `unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M` | about 18 GB |

Tips:
- Give Docker Desktop enough memory: about 8 GB for the 4B model, at least 24 GB for 30B-A3B.
- Context length defaults to 16,384 tokens; change it with `CTX` in `.env`. Larger context uses more memory.
- Any instruct GGUF that llama.cpp supports will load. Prefer Q4_K_M quants; mixture-of-experts models give the best speed per GB of memory.
- On a Mac, Docker has no GPU access, so models run on the CPU and are slower than native.
- Measured speeds per machine go in [`bench/`](bench/) (`pai-bench`). We publish numbers only after measuring them.

### Optional cloud model

For setup or a machine too small for a local model, LiteLLM can route to a cloud model (OpenRouter by default, `OPENROUTER_MODEL` in `.env`). Your messages then leave the computer. It is off by default; type the provider key into the PAI app yourself, never into `.env` in plain text or into a chat with an agent. Free model IDs change often: check openrouter.ai/models.

---

## Day-to-day

| Task | Command (run in `prototype/`; `scripts/pai-up` passes the vault key) |
|---|---|
| Status | `docker compose --profile local ps` |
| Logs | `docker compose --profile local logs --tail 50 app llm litellm` |
| Stop | `docker compose --profile local stop` |
| Start | `scripts/pai-up --profile local up -d` |
| Update | `git pull`, then `scripts/pai-up --profile local up -d --build` |

The audit log stores metadata only. Set `AUDIT_CONTENT=1` in `.env` to also store prompts and replies (encrypted, but more sensitive).

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `port is already allocated` on 8088 | Another program uses it. Set `PAI_PORT=8089` in `.env` and use that port. |
| `llm` container exits with code 137 | Out of memory. Raise Docker's memory or switch back to the 4B model. |
| Health check never returns 200 | `docker compose --profile local logs --tail 60 app`. A "vault" error means a wrong or missing key; a LiteLLM error means check the `litellm` container. |
| First answer is very slow | The model or voice models are still downloading: `docker compose --profile local logs --tail 20 llm speaches`. |
| Slow on Apple Silicon | Expected in Docker (CPU only). Use the 4B model or run llama.cpp natively. |
| `secrets` error on start | Docker Compose is too old. Upgrade Docker. |
| Voice does not work | Check the `speaches` container is running and the browser has microphone permission for localhost. |

Still stuck? Email `agents@freedomos.org` with `[install]` in the subject (see [CONTRIBUTING.md](CONTRIBUTING.md)), or open an issue with the exact command, the error text, and the output of `docker compose --profile local ps`.

---

## Security notes

- PAI has **no login yet**. Anyone who can reach port 8088 can read memories and confirm actions. It binds to `127.0.0.1` by default: keep it on this computer or a private network and never publish the port.
- The vault key lives outside `.env` and outside the app container's environment. Lose the key and the vault cannot be opened.

---

## Get involved

- **Roadmap:** [ROADMAP.md](ROADMAP.md)
- **Mailing list, agent request inbox, pull requests:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security reports:** [SECURITY.md](SECURITY.md)

---

## Repository map

| Path | What it contains |
|---|---|
| [`INSTALL.md`](INSTALL.md) | Full install guide, with a copy-paste prompt for your AI agent. |
| [`SPEC.md`](SPEC.md) | Technical specification of every subsystem. |
| [`prototype/`](prototype/) | The PAI app (FastAPI, React UI, vault, router) and its Docker Compose stack. |
| [`os/`](os/) | Early `bootc` and provisioning work for the future PAI OS image. |
| [`bench/`](bench/) | `pai-bench`: token speed, power and noise measurements. |
| [`docs/`](docs/) | Architecture notes and research. |
| [`docs/agent-workflows/`](docs/agent-workflows/) | How agents handle emailed requests, by type. |
| [`infra/email/`](infra/email/) | Cloudflare Email Worker and runbook for the project addresses. |

---

## License

PAI OS is free and open source under the [GNU AGPL-3.0](LICENSE). If you run a modified version as a network service, you must offer its source to the people who use it. Paid support is optional: $59 a year.
