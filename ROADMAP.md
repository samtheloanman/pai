# PAI Roadmap

What we are building next for the PAI software. Dates are targets, not promises. Each item links to its requirement ID in [PRD.md](PRD.md). Want to help with one? See [CONTRIBUTING.md](CONTRIBUTING.md).

Status key: **Done** · **In progress** · **Next** · **Later**

## Now: M0 prototype (Nov–Dec 2026)

Goal: a fresh machine goes from power-on to a useful local assistant without a terminal.

| Item | PRD | Status |
|---|---|---|
| Docker prototype: local model, voice, vault, approvals, audit log | — | Done |
| Install guide an AI agent can follow ([INSTALL.md](INSTALL.md)) | — | Done |
| First-boot interview and "what I will and won't do" page | APP-3, APP-4 | In progress |
| Memory you can view and delete (SQLite + sqlite-vec) | APP-5 | In progress |
| Every send / delete / spend action asks first | APP-12 | In progress |
| Installable web app (PWA) on phone and desktop | APP-1 | Next |
| Pairing by QR code onto a private network | APP-2 | Next |
| Connectors: calendar, email, local folders (each off by default) | APP-6 | Next |
| Telegram channel with "not end-to-end encrypted" note | APP-7 | Next |
| Privacy level shown per channel | APP-11 | Next |
| `pai-bench` numbers for the reference machines | — | Next |

## Next: PAI OS image (early 2027)

| Item | PRD | Status |
|---|---|---|
| bootc image with A/B updates and automatic rollback | OS-1..OS-8 | Next |
| Database-safe updates and pre-update backup | OS-10 | Next |
| Factory reset back to first boot | OS-12 | Next |
| Ansible playbook for dev boxes | OS-9 | Next |
| No login → owner login and session handling | — | Next |

## Later (2027)

| Item | PRD | Status |
|---|---|---|
| Signal and Matrix channels | APP-10 | Later |
| Email channel: message PAI, get a reply | APP-8 | Later |
| Weekly 2-minute check-in | APP-9 | Later |
| More local models tested and documented per RAM size | — | Later |
| Native (non-Docker) install for Apple Silicon GPU speed | — | Later |

## Not planned

- A PAI cloud or PAI account that holds your data.
- Running trillion-parameter frontier models at home.
- Official WhatsApp or iMessage bots (owner-installed only, unsupported).

## How the roadmap changes

Proposals go to the mailing list with `[RFC]` in the subject. Agreed items get a GitHub issue and a row here in the same pull request.
