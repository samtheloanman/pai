# Session checkpoint, 1 Nov 2026

## Done
| Area | State | Evidence |
|---|---|---|
| Store (`pai-store`) | Live preview on Vercel; local build on port 3031 | Next.js 16 + Payload 3.92.1; 8 products with 3-image flat-illustration galleries; 6 guide pages with diagrams |
| Docker prototype (`prototype/`) | Running on 127.0.0.1:8088 | 4 containers: app, litellm, speaches, llm; interview, rules, chat, memory, voice tested end to end with the 4B model |
| Chat front end | Restyled | React + assistant-ui + Geist, teal accents; verified with a real message |
| MVP app (`prototype/`, branch `feat/mvp-app`, tasks 1-8) | Built; checked against a local server with a fake LiteLLM | Encrypted vault with hybrid search, tiered routing, hash-chained activity log, confirm gate, opt-in cloud providers with hard blocks, React views (Chat, Approvals, Activity, Memory, Rules, Setup, Providers), e2e script `prototype/app/run-e2e.sh` |
| Tests | Passing | 171 back-end (plus 1 e2e run separately) and 13 front-end tests on `feat/mvp-app` |
| Base OS research | Notes written | `docs/AI-OS-BASE-RESEARCH.md`: NixOS or Fedora bootc for the headless base; Omarchy optional on a Dev image |
| App replacement tools | Candidates listed only | `docs/APP-REPLACEMENT-ENGINE.md`; nothing integrated or tested |

## Not done
- OS image and hardware; hardware tests pending.
- Telegram and email channels.
- Presidio (PII) masking before cloud calls.
- Learning beyond stored memories; network awareness.
- Real full-stack Docker Compose run of the MVP: pending (e2e used a fake LiteLLM).
- Route bench has not been run: no accuracy or speed numbers yet.

## Decisions recorded
- Commit the prototype to GitHub on a feature branch: done (`feat/docker-prototype`).
- Hardware spend and supplier outreach: **on hold** until Alibaba candidate specs and unit economics are confirmed by Sam.
- Base OS: headless atomic image (NixOS or Fedora bootc, chosen by prototyping); Omarchy only as an optional desktop/Dev image.
- Next UI work: the PAI chat screen first, then website polish.

## Still unconfirmed
- Strix Halo graphics support on NixOS vs Fedora bootc.
- Licenses of the guard models: Llama Guard is under a restricted community license; Granite Guardian and others need a model-card check.
- Omarchy funding and long-term plan.
- Whether free OpenRouter models are suitable for the setup mode (answers leave the box; model IDs change).

## Later (queued, not designed)
- File sync between devices with Syncthing; client-side encrypted offsite backup (restic or Rclone Crypt).
