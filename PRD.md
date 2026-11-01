# PAI — Product Requirements (MVP)

Version 0.1 · 1 Nov 2026 · Owner: Sam · Status: draft for review

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
| OS-1 | Headless Linux image for x86-64; immutable root with A/B partitions and automatic rollback on failed boot | Must |
| OS-2 | Signed update images; box refuses unsigned images | Must |
| OS-3 | llama.cpp (Vulkan on AMD iGPU) behind llama-swap; OpenAI-compatible API bound to localhost | Must |
| OS-4 | Bundled models chosen per memory size: 16 GB → 7-14B and gpt-oss-20b; 32 GB → 20-30B MoE (e.g. Qwen3-30B-A3B). License check per model card before bundling | Must |
| OS-5 | Nothing listens on public interfaces; services bind to localhost and the private overlay network only | Must |
| OS-6 | Remote access through Tailscale client; default = owner's own Tailscale account; Headscale option designed in, shipped later | Must (default), Later (Headscale) |
| OS-7 | Telemetry off by default; no outbound calls except updates and channels the owner enables | Must |
| OS-8 | Install path for PAI OS on own hardware: USB image, ≥16 GB RAM, wired network | Must |
| OS-9 | Ansible playbook that provisions a dev box to the same state as the image | Should |

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

## 11. Open decisions (Sam)
- Pricing strategy for hardware (software-first vs repriced hardware).
- Test-unit spend and RFQ sends.
- OS base: bootc/Fedora CoreOS-style vs Ubuntu Core (decide by prototyping).
- Voice layer later: OpenVoiceOS vs Home Assistant Wyoming (hands-on test first).
- Launch languages.
