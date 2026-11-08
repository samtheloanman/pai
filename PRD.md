# PAI — Product Requirements (MVP)

Version 0.2 · 1 Nov 2026 · Owner: Sam · Status: draft for review

v0.2 adds: base OS choice, model providers and routing, private cloud routing, encrypted vault, audit trail, learning, tool sandbox, LAN awareness, database-safe updates. Items marked (U) are unconfirmed and must be checked on real hardware or against official docs.

## 1. Summary

PAI is a private AI server for the home. It runs open-weight models on a small box, learns about its owner through a first-boot interview, and answers through the PAI app and chat apps the owner already uses. Tagline: **Your AI. Your house.**

This PRD covers the MVP: the PAI software (PAI OS + PAI app) and the first hardware (PAI Starter). Pro, Edge, GPU dock and Dev images are out of MVP scope except where noted.

All copy follows [docs/BRAND-CLAIMS.md](docs/BRAND-CLAIMS.md). No speed, power or noise numbers are published until `pai-bench` measures them.

## 2. Problem

- People who want a capable assistant have to send their messages, files and history to a company's servers.
- Self-hosting open models works, but needs Linux, model, networking and update skills most people do not have.
- In the $1-2k band nobody ships a finished, supported, chat-first private AI appliance (Oct 2026 market research).

## 3. Users

| Persona | Need | MVP? |
|---|---|---|
| Privacy-minded professional | Assistant over email, calendar and files without a cloud account | Yes (primary) |
| Home-lab owner | Box or image that is open, extensible and runs on own hardware | Yes (PAI OS) |
| Small office | Shared assistant on the office network | Later |
| Non-technical household | Appliance that never needs a terminal | Later (needs Care + polish) |

## 4. Goals and non-goals

Goals
1. A box that goes from unboxing to first useful answer in under 30 minutes, with no terminal.
2. Every conversation's inference runs on the box.
3. The owner can see and edit what PAI knows about them.
4. Updates never leave the box unbootable (A/B with rollback).
5. Same software sold as PAI OS for the owner's own x86 box.

Non-goals (MVP)
- Medical, legal or financial advice features. PAI is not a medical device.
- Frontier-scale models; trillion-parameter models stay in datacenters.
- A PAI cloud account that stores user data.
- Supported WhatsApp or iMessage (optional, unsupported only).
- Windows or macOS hosts.

## 5. MVP scope — PAI software

### 5.1 PAI OS (box image)

| ID | Requirement | Priority |
|---|---|---|
| OS-1 | Headless image built with bootc on a **Fedora** base (not CentOS Stream: its kernel is too old for new AMD chips); atomic updates with automatic rollback when post-boot health checks fail (greenboot). Final choice after the hardware test in §6.2; NixOS is the fallback | Must |
| OS-2 | Signed update images; box refuses unsigned images | Must |
| OS-3 | llama.cpp (Vulkan on AMD iGPU) behind llama-swap; OpenAI-compatible API bound to localhost | Must |
| OS-4 | A 4B model (~2.5 GB) ships inside the image so setup and chat work offline on first boot. Larger models chosen per memory size: 16 GB → 7-14B and gpt-oss-20b; 32 GB → 20-30B MoE (e.g. Qwen3-30B-A3B). License check per model card before bundling | Must |
| OS-5 | Nothing listens on public interfaces; services bind to localhost and the private overlay network only | Must |
| OS-6 | Remote access through Tailscale client; default = owner's own Tailscale account; Headscale option designed in, shipped later | Must (default), Later (Headscale) |
| OS-7 | Telemetry off by default; no outbound calls except updates and channels the owner enables | Must |
| OS-8 | Install path for PAI OS on own hardware: USB image, ≥16 GB RAM, wired network | Must |
| OS-9 | Ansible playbook that provisions a dev box to the same state as the image | Should |
| OS-10 | Database-safe updates: migrations stay readable by the previous app version for one release (add, never rename or drop); the app refuses to start on a newer schema it does not know, with a clear message; a consistent SQLite backup is taken before every OS update and restored only as a last resort | Must |
| OS-11 | No desktop or GUI packages on consumer images; Omarchy only as an optional Dev image | Must |
| OS-12 | Factory reset wipes owner state (vault, audit log, keys, accounts) and returns to first boot; built by us, since bootc has no built-in state wipe (U) | Must |

### 5.2 PAI app and agent

| ID | Requirement | Priority |
|---|---|---|
| APP-1 | Installable web app (PWA) served by the box over the private network; works on iPhone Safari, Android Chrome, iPad, desktop Chrome | Must |
| APP-2 | Pairing: owner scans a code from the box's first-boot screen to join the private network and open the app | Must |
| APP-3 | First-boot interview (~15 min): who you are, apps you use, what you want help with, what is off-limits | Must |
| APP-4 | Interview output: local profile + plain-English "what I will and won't do" page the owner can edit | Must |
| APP-5 | Personal memory in SQLite + sqlite-vec on the box; owner can view and delete any memory item | Must |
| APP-6 | Connectors: calendar (CalDAV / Google OAuth), email (IMAP/SMTP), local folders; each off until enabled | Must |
| APP-7 | Chat over Telegram (long polling, no inbound port) with an in-app note that Telegram is not end-to-end encrypted | Must |
| APP-8 | Email channel (send PAI a message, get a reply) | Should |
| APP-9 | Weekly 2-minute check-in that updates the profile | Should |
| APP-10 | Signal and Matrix channels | Month 1 |
| APP-11 | Privacy level shown per channel (A stays home / B end-to-end encrypted / C third party carries it) | Must |
| APP-12 | Every tool action that sends, deletes or spends asks the owner first | Must |

### 5.3 Acceptance for software MVP
- Fresh box: power on → pairing → interview → first calendar question answered over the PAI app, under 30 minutes, no terminal (timed with 3 testers).
- Pull power during an update → box boots the previous version.
- `ss -tlnp` on the box shows no service on a public interface.
- Telegram chat works end to end; the app shows its privacy level C note.

### 5.4 Model providers and routing

| ID | Requirement | Priority |
|---|---|---|
| ROUTE-1 | LiteLLM is the single model router for the app, voice and agents | Must |
| ROUTE-2 | Built-in engine: llama.cpp. Optional external backends: Ollama, LM Studio (owner-installed; LM Studio is closed-source and is never bundled) | Must / Should |
| ROUTE-3 | Cloud providers OpenRouter, Hugging Face and NVIDIA are available only with the owner's own key, stored encrypted; **no cloud provider by default**; no shared PAI keys in the image | Must |
| ROUTE-4 | Request routing in tiers: (1) fixed rules, (2) small local embedding matcher (e.g. all-MiniLM-L6-v2, license to confirm), (3) the already-loaded main model with a structured decision prompt in its own server slot, only for unclear requests | Must |
| ROUTE-5 | Any send, delete, spend or system change requires the owner's confirm regardless of what any model decides | Must |
| ROUTE-6 | Routing accuracy and added latency measured in pai-bench on a labelled request set before targets are published | Must |
| ROUTE-7 | Multi-box request distribution with NVIDIA Personal AI Router (PAIR) | Later |
| ROUTE-8 | "Big model, slow mode": larger MoE models read from the NVMe SSD for background jobs only, never chat or voice; speeds measured in pai-bench before any claim | Later |

### 5.5 Private cloud routing

| ID | Requirement | Priority |
|---|---|---|
| PRIV-1 | Cloud use is opt-in per owner and visible per request | Must |
| PRIV-2 | Before any cloud call, a local detector (Presidio via LiteLLM's guardrail, or similar) masks names, emails and similar with reversible placeholders and restores them in the reply | Should |
| PRIV-3 | Secrets, financial identifiers and the owner's off-limits topics block cloud use outright | Must |
| PRIV-4 | Every outbound call is logged with provider, size and masked-field count (see AUD) | Must |
| PRIV-5 | Free cloud tiers are assumed to log prompts; only masked or non-sensitive text goes there | Must |

### 5.6 Encrypted vault

| ID | Requirement | Priority |
|---|---|---|
| VAULT-1 | One SQLite vault file encrypted with SQLCipher, holding facts, memories, full-text index (FTS5) and vectors (sqlite-vec); hybrid search | Must |
| VAULT-2 | Full-disk encryption (LUKS); vault key sealed to the box's TPM with an optional owner PIN (TPM on Starter candidates U) | Must |
| VAULT-3 | Passwords and card numbers live in a separate vault excluded from assistant search by default | Must |
| VAULT-4 | Move vectors to LanceDB if a vault outgrows sqlite-vec; threshold set by pai-bench | Later |
| VAULT-5 | Backups encrypted on the box before upload (restic) to storage the owner chooses | Should |

### 5.7 Audit trail

| ID | Requirement | Priority |
|---|---|---|
| AUD-1 | Every model call (via a LiteLLM callback), routing decision, agent action, confirm, system change, outbound call, memory change and training run writes one audit entry through a single function | Must |
| AUD-2 | Entries store metadata only by default; full prompt and reply content is an owner opt-in with its own retention | Must |
| AUD-3 | Append-only, hash-chained entries in a separate SQLCipher file; a verifier reports the first broken entry | Must |
| AUD-4 | Activity page: what PAI did, what left the box, what asked for confirmation; filter and export | Should |
| AUD-5 | Field names follow OpenTelemetry conventions so logs can be exported to Langfuse or similar | Should |

### 5.8 Learning from the owner

| ID | Requirement | Priority |
|---|---|---|
| LEARN-1 | Memory first: facts and preferences learned instantly, visible and deletable on the Memory page | Must |
| LEARN-2 | Owner-approved updates to the rules page from corrections (playbook style) | Should |
| LEARN-3 | Prompt tuning of the decision step from confirm/reject history (DSPy-style), no GPU needed | Later |
| LEARN-4 | LoRA training (Soup, Unsloth or TRL) weekly on a GPU machine, off by default, promoted only if it beats the current adapter on a held-out and regression set, with one-switch rollback; deleted memories are excluded from the next run | Later |

### 5.9 Tool sandbox

| ID | Requirement | Priority |
|---|---|---|
| TOOL-1 | Generated or third-party tools run in throwaway, unprivileged Podman containers with a read-only filesystem | Must |
| TOOL-2 | Tools have no access to the vault, audit log or keys; login tokens come from a separate token keeper | Must |
| TOOL-3 | Network access only to destinations the tool declares | Must |
| TOOL-4 | Automating a third-party site requires a per-service policy check against its terms; official APIs and MCP servers first | Must |

### 5.10 Home network awareness

| ID | Requirement | Priority |
|---|---|---|
| LAN-1 | Passive new-device alerts (ARP/NDP listener); no active network scans | Should |
| LAN-2 | PAI does not intercept other devices' DNS or traffic in MVP: that only works if PAI is the home router, which is an open decision | Must |

## 6. MVP scope — hardware

### 6.1 PAI Starter

| Item | Requirement |
|---|---|
| Platform | Ryzen 8745HS/8845HS/8945HS-class mini PC, Radeon iGPU |
| Memory | 2 SO-DIMM slots; ships 1 × 16 GB (Starter 16) or 32 GB (Starter 32); second slot free |
| Expansion | OCuLink port for the GPU dock; USB4; 2.5 GbE |
| Storage | 1 TB NVMe |
| Certification | Off-the-shelf barebone with existing FCC/CE IDs; no custom radios |
| Upgrade path | memory → GPU dock → second box (llama.cpp RPC) — see docs/EXTENDABLE.md |
| Disclosure | Single-channel trade-off with one stick stated on the product page and FAQ |

### 6.2 Hardware gates before any price is public
1. Test units ordered (one Starter-class box, one edge candidate) — Sam approves spend.
2. RFQs to GMKtec, Minisforum, Beelink and the edge seller for 100 units with memory factory-installed, plus FCC/CE IDs.
3. `pai-bench` run on each stage (base, full memory, dock, second box).
4. Retail price set from quotes; break-even check (fees ~8%, warranty reserve 5%, shipping, ~$100 margin).

## 7. Measurement — pai-bench

See [bench/README.md](bench/README.md). Output rows in `bench/results/` are the only source for any speed, power or noise number on the store, spec sheet or Kickstarter page.

## 8. Pricing (current)

| SKU | Price |
|---|---|
| PAI OS | $59 |
| PAI OS + Onboarding Kit | $149 |
| PAI Care (1 year) | $99 |
| Hardware (Starter, Pro, Edge, Dock) | announced at launch, from quotes |

Memory prices roughly doubled in 2026; parts-cost break-even for a 32 GB box is ≈ $1,366 at retail parts prices. Factory-installed memory quotes are the path to a sub-$1k Starter.

## 9. Milestones

| Milestone | Target | Exit criteria |
|---|---|---|
| M0 Prototype | Nov-Dec 2026 | OS-1..OS-8 + APP-1..APP-7 on a test box; bench rows for Starter; video footage of the real unit |
| M1 Campaign | early 2027 | Prices from quotes; claims lint clean; pre-launch page live |
| M2 Batch 1 | +1-3 months | 100-300 units; APP-10 Signal/Matrix |
| M3 Ship | +4-5 months | PAI OS first, then Starter |

## 10. Risks

| Risk | Mitigation |
|---|---|
| DRAM prices | 1-stick base, free slot, factory-RAM quotes, price holds |
| Messaging platforms change rules | Promise only PAI app, Telegram, email; Signal/Matrix next |
| Support load | Immutable OS, rollback, PAI Care |
| Model license changes | License check per model card before bundling |
| Exposed agent gateways (40k+ OpenClaw instances found exposed, Feb 2026) | OS-5; CI test that fails if any port binds 0.0.0.0 |
| OS rolls back but the database already migrated | OS-10 |
| Generated tools damage data or leak keys | TOOL-1..TOOL-3 |
| Cloud provider sees private data | ROUTE-3, PRIV-1..PRIV-5 |
| Routing call slows simple requests | ROUTE-4 tiers, ROUTE-6 measurement |

## 11. Open decisions (Sam)
- Pricing strategy for hardware (software-first vs repriced hardware).
- Test-unit spend and RFQ sends.
- OS base: Fedora bootc chosen, pending a test on real Starter and Pro hardware (graphics acceleration, Wi-Fi, rollback after a deliberately broken update, factory reset).
- Whether PAI ever becomes the home router (needed for any network-wide protection).
- NVMe SSD choice for big-model mode (needs a sustained-read test).
- Voice layer later: OpenVoiceOS vs Home Assistant Wyoming (hands-on test first).
- Launch languages.
