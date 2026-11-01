# PAI — Build plan (v1, 2026-10-31)

One plan, four tracks, in order. Nothing outward-facing (deploy, vendor email, Kickstarter) runs without Sam's OK.

## Where things stand
- **Store** `~/Code/pai-store`: Payload 3.92.1 ecommerce (MIT), Next.js, Postgres, Stripe, Vercel Blob. Runs locally on :3030; admin `sam@c-mtg.com`; type-check clean; production build verifying. Software SKUs live, hardware SKUs draft.
- **Hardware**: DRAM prices kill a 64 GB box under $1k. Best starter design: Ryzen 8945HS mini PC (GMKtec K11 class), 2 SO-DIMM slots, OCuLink, ships with 1×16 or 1×32 GB, upgrade with RAM, then a GPU dock, then a second node (`hardware/EXTENDABLE.md`).
- **Alibaba candidates (4 links from Sam)**: blocked by CAPTCHA. Need specs pasted or the CAPTCHA solved by hand.

---

## Track 1 — Lock the hardware lineup (decide first; everything else depends on it)

| SKU | Role | Box | Memory | Target retail |
|---|---|---|---|---|
| PAI Starter | volume, < $1k | Ryzen 8945HS / 8845HS mini PC, OCuLink, 2× SO-DIMM | 1×16 GB (slot 2 empty) | $899–999 |
| PAI Starter+ | same box | 2×16 GB dual channel | $1,199 |
| PAI Dock | upgrade | OCuLink dock, customer brings a tested GPU | — | $199 (dock only) |
| PAI Pro | big models | Strix Halo 128 GB | soldered 128 GB | $4,499 |
| PAI Edge AIO (new) | kitchen/office screen | fanless all-in-one (Alibaba candidates) as a **display/voice terminal** that talks to a PAI box; not the inference node unless specs say otherwise | 8–16 GB | TBD |

Steps:
1. Sam: paste specs for the 4 Alibaba links (CPU, RAM type/slots, ports, screen, price at 1/50/200 units, FCC/CE).
2. Order **one** of each candidate for testing: Starter box, one Alibaba edge/AIO unit. (Sam approves spend.)
3. RFQ to GMKtec / Minisforum / Beelink / the Alibaba seller for 100-unit pricing **with RAM installed by the factory** (cheapest path to margin). Sam sends.

Decision gate: retail price per SKU set from real quotes, not street prices.

## Track 2 — Accurate model performance (measure, don't quote)

Build `pai-bench` (one script, runs on every box and stage):
- Engine: llama.cpp (Vulkan on AMD iGPU and Strix Halo; CUDA on any NVIDIA dock GPU) using `llama-bench` plus a real chat replay.
- Models: Qwen3-30B-A3B Q4_K_M, gpt-oss-20b, Gemma-class 12B, a 7–8B dense model; on Pro add gpt-oss-120b.
- Measures: prompt-processing t/s at 512 and 4k tokens, decode t/s, time to first token, peak memory, wall watts (smart plug), noise (phone dB meter at 1 m).
- Stages per box: base RAM → full RAM → + GPU dock → + second node (RPC).
- Output: JSON to `bench/results/`, plus one Markdown table that the store and Kickstarter page pull numbers from. No speed claim goes public without a row here.

## Track 3 — Software on the box + UI on every device

Box image (PAI OS):
- Headless Linux, immutable with A/B rollback for the consumer SKUs; Omarchy 4 desktop only on a Dev image.
- llama.cpp + llama-swap (OpenAI-compatible API on localhost), SQLite + sqlite-vec memory, the "grill me" onboarding agent.
- Private overlay network for remote access and box-to-box mesh; nothing listens on public interfaces. Default design: stock Tailscale client (open source, BSD-3) pointed at a **Headscale** control server (open source Tailscale-compatible coordinator). Fallbacks to evaluate: NetBird (fully open source incl. server), Nebula (no coordinator needed beyond a lighthouse), plain WireGuard. Decision still open: who runs the coordinator (see "Overlay decision" below). Linux module/package details: `hardware/MESH-LINUX.md`.

**Overlay decision (open, Sam):**
| Option | Who sees metadata | Setup for a non-technical owner | Risk |
|---|---|---|---|
| A. Owner's own Tailscale account (free tier) | Tailscale Inc. (not traffic; WireGuard is end to end) | easiest: sign in once | third-party control plane; terms/pricing can change |
| B. PAI-run Headscale (Care subscription) | PAI (device list, IPs, not traffic) | easy: pairing code | PAI becomes a single point of failure and holds metadata; must be hosted and kept up |
| C. Owner-run Headscale/NetBird on a small VPS or the box with a public endpoint | owner only | hard | needs a public IP/DDNS/tunnel; support burden |
| D. Nebula | owner only | medium | needs a lighthouse with a public IP |
Default for launch: **A**, with **B** as the paid "no third party" upgrade. Both use the same client, so switching is a config change.

UI surfaces (same backend API):
| Device | Surface | Ships |
|---|---|---|
| Phone / tablet / laptop | PAI web app (PWA) over Tailscale; installable | launch |
| Any chat app | Telegram bot, email (IMAP), Signal; WhatsApp/iMessage optional and documented as unsupported | launch / month 1 |
| Edge AIO screen | same PWA in kiosk mode (Chromium `--kiosk`), wake word + push-to-talk voice | after Track 1 picks the unit |
| Desktop on the box | Omarchy Dev image only | Dev SKU |

Test matrix: iPhone Safari, Android Chrome, iPad, Mac/Windows Chrome, AIO kiosk — checked with Playwright device emulation plus one real phone.

## Track 4 — Store and launch site

Already done: Payload store, PAI palette, products seeded, migrations, Blob storage.
Remaining:
1. Production build green (in progress) → commit.
2. Replace template home page with the PAI landing page (hero, 3 proofs, privacy-tier channel table, SKU cards, email capture) built as Payload blocks so it stays editable in admin.
3. Product pages: specs table + bench table from Track 2, upgrade-path diagram, "what it runs at each stage".
4. Stripe test mode end to end (cart → checkout → order in admin).
5. Vercel: create project, Postgres (Neon or Supabase), Blob store, env vars (`DATABASE_URL`, `PAYLOAD_SECRET`, `BLOB_READ_WRITE_TOKEN`, Stripe keys, `NEXT_PUBLIC_SERVER_URL`). **Needs Sam's OK** (deploy + new provider resources).
6. Playwright smoke suite (home, shop, product, cart, checkout, admin login) on desktop + mobile viewports; runs in CI on the Dell runners.

## How agents are used ("headless browser agents")
- **Store config**: Playwright scripts drive the Payload admin to create/update pages, products, and media from files in `aios/projects/pai/` — repeatable, versioned, no hand clicking. Same scripts verify the result.
- **Vendor research**: browser agents read vendor stores and spec sheets. Anything behind a CAPTCHA or login (Alibaba, fccid.io) is handed to Sam; agents don't bypass bot checks.
- **Box configuration**: not a browser job. Ansible playbook + the PAI OS image configure the physical machines; `pai-bench` verifies them.

## Order of work
1. Today: finish build, commit, push store repo (private GitHub). 
2. Sam: Alibaba specs + approve test-unit purchases + pick Vercel DB provider.
3. Write `pai-bench` and the Ansible/OS skeleton while units ship.
4. Landing page + product pages (numbers stay "TBD" until bench).
5. Units arrive → bench → set prices → publish hardware SKUs → deploy to Vercel.
