# PAI — Private AI Home Server

> **Your AI. Your house.**

PAI is a private, sovereign AI server for the home. It runs state-of-the-art open-weight language and voice models on a compact, silent appliance, learns about its owner through a first-boot interview, and provides natural assistance over web, voice, and existing chat applications without cloud reliance.

---

## System Architecture

```
                                  ┌──────────────────────────────┐
                                  │       Client Interfaces      │
                                  │ (Web PWA / iOS / Voice / CLI)│
                                  └──────────────┬───────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ PAI Appliance Base OS (bootc / Fedora CoreOS / ostree A/B Rollback)                    │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ PAI Application Server (Port 8088 - FastAPI + @assistant-ui/react)             │   │
│   │                                                                                │   │
│   │   ┌───────────────────┐    ┌────────────────────┐    ┌─────────────────────┐   │   │
│   │   │  Setup Interview  │    │ Multi-Tier Router  │    │   Encrypted Vault   │   │   │
│   │   │ (8-Question Flow) │    │(Rules / Embeddings)│    │(SQLCipher+Vec+FTS5) │   │   │
│   │   └───────────────────┘    └─────────┬──────────┘    └─────────────────────┘   │   │
│   │                                      │                                         │   │
│   │   ┌───────────────────┐              │               ┌─────────────────────┐   │   │
│   │   │  Confirm Gateway  │              │               │ Tamper-Evident Log  │   │   │
│   │   │ (Approvals / TTL) │              │               │(Append-Only Ledger) │   │   │
│   │   └───────────────────┘              │               └─────────────────────┘   │   │
│   └──────────────────────────────────────┼─────────────────────────────────────────┘   │
│                                          │                                             │
│                                          ▼                                             │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ LiteLLM Model Gateway (Port 4000)                                              │   │
│   │                                                                                │   │
│   │   ┌───────────────────────┐                    ┌───────────────────────────┐   │   │
│   │   │ Local llama.cpp:8080  │                    │ User-Keyed Cloud Fallback │   │   │
│   │   │ (Qwen3-4B / 14B / 30B)│                    │ (OpenRouter/NVIDIA/HF)    │   │   │
│   │   └───────────────────────┘                    └───────────────────────────┘   │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Local Voice Engine (Port 8000 - faster-whisper + Kokoro TTS)                   │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                        │
│   ┌────────────────────────────────────────────────────────────────────────────────┐   │
│   │ App Replacement & LAN Guardian (Unprivileged Podman Sandboxes)                 │   │
│   │ • REA & CLI-Anything   • Passive ARP Listener   • Unbound DNS Sinkhole         │   │
│   └────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quickstart (Zero-Config 1-Click Launch)

Run one command to start PAI OS with local Ollama:
```bash
./run.sh
```
Or via Docker Compose directly:
```bash
docker compose up -d
```

### Open the Interface
Navigate to [http://localhost:8088](http://localhost:8088) in your browser:
1. **Setup Interview**: Complete the 8-question first-boot interview by voice or keyboard to personalize your assistant.
2. **Constitutional Rules**: Review and confirm the auto-generated boundaries ("I will / I won't").
3. **Compile & Activate**: Hit **Compile & Activate** to generate your sovereign companion persona (`pai-default`), auto-bind local tools, and enable encrypted memory persistence.
4. **Chat & Voice**: Real-time conversation with local speech input/output, zero cloud leak guarantee.

---

## Cinematic Launch Trailer

Watch the *Her* OS1 setup sequence recreated for PAI OS:  
[![PAI OS Marketing Trailer](https://img.youtube.com/vi/f9Hg1x-Ctlw/0.jpg)](https://www.youtube.com/watch?v=f9Hg1x-Ctlw)  
*Video Reel: `pai-os-her-marketing-9x16.mp4` (50s vertical, 30fps, 44.1kHz stereo audio master).*

---

## Store & Website
Pre-order dedicated hardware appliances or read live deployment guides at [pai-store.vercel.app](https://pai-store.vercel.app).

| Directory | What it contains |
|---|---|
| [`INSTALL.md`](INSTALL.md) | Install the Docker prototype yourself or with your AI agent (includes copy-paste prompt) |
| [`SPEC.md`](SPEC.md) | **Complete technical system specification** and subsystem documentation. |
| [`PRD.md`](PRD.md) | Product requirements, personas, hardware targets, and scope boundaries. |
| [`prototype/app/`](prototype/app/) | The PAI application core: FastAPI, React UI, SQLCipher vault, and routing tiers. |
| [`os/`](os/) | `bootc` Containerfiles and systemd Quadlet provisioning configurations. |
| [`bench/`](bench/) | `pai-bench`: Benchmark harness for token speeds, power draw, and acoustic noise. |
| [`docs/`](docs/) | Architecture records, LLM council verdicts, and brand claims guidelines. |

---

## Hardware Lineup & Roadmap

- **PAI Starter ($899–$999)**: AMD Ryzen 8945HS mini PC, 16 GB DDR5, OCuLink expansion port.
- **PAI Starter+ ($1,199)**: 32 GB dual-channel DDR5 for 20B–30B mixture-of-experts models.
- **PAI Dock ($199 bare)**: OCuLink external GPU dock for desktop graphics cards.
- **PAI Pro ($4,499)**: AMD Strix Halo APU with 128 GB unified memory for 70B+ frontier models.

---

## Store & Website
The commercial storefront and documentation portal live in `samtheloanman/pai-store` running Next.js + Payload CMS at [http://localhost:3031](http://localhost:3031).
