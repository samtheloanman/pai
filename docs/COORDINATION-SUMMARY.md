# Session checkpoint, 1 Nov 2026

## Done
| Area | State | Evidence |
|---|---|---|
| Store (`pai-store`) | Live preview on Vercel; local build on port 3031 | Next.js 16 + Payload 3.92.1; 8 products with 3-image flat-illustration galleries; 6 guide pages with diagrams |
| Docker prototype (`prototype/`) | Running on 127.0.0.1:8088 | 4 containers: app, litellm, speaches, llm; interview, rules, chat, memory, voice tested end to end with the 4B model |
| Chat front end | Restyled | React + assistant-ui + Geist, teal accents; verified with a real message |
| Tests | Passing | 10 back-end and 3 front-end tests |
| Base OS research | Notes written | `docs/AI-OS-BASE-RESEARCH.md`: NixOS or Fedora bootc for the headless base; Omarchy optional on a Dev image |
| App replacement tools | Candidates listed only | `docs/APP-REPLACEMENT-ENGINE.md`; nothing integrated or tested |

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
