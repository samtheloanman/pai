# PAI: security-first path to a private, headless, easy-to-install box

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:subagent-driven-development or superpowers:executing-plans. Each phase is one PR on a `<agent>/<slug>` branch in its own worktree. Write the failing test first. Steps use `- [ ]` checkboxes.

Date: 2026-11-24. Owner decision recorded the same day: privacy and network security are the top priority, and they ship in the open-source PAI OS, not only on PAI hardware.

## Goal

A person installs PAI on bare metal or in Docker, never opens a terminal after that, and reaches it from their phone over a private network. Data stays on the box by default, and is protected as far as possible when a cloud model is used.

## Decisions taken from the 2026-11-24 research

| Topic | Decision | Why |
|---|---|---|
| OS image | Keep Fedora bootc. Add greenboot-rs for rollback. Build with the unified `image-builder` CLI. | bootc is the only option with A/B images and ordinary Linux packages. bootc itself does not roll back automatically. `bootc-image-builder` and the Anaconda ISO type are deprecated. |
| Existing Linux box | Signed install script that verifies before it runs, plus Compose. | Olares ships the same three paths (image, script, Compose). |
| Ansible (OS-9) | Dev boxes only. Not an end-user installer. | A second definition of the box drifts from the Containerfile. |
| Phone access | Private network and installable web app first. No chat gateway needed for this. | The app binds to `127.0.0.1:8088` and has no login today. |
| Chat gateway | Later phase. Hermes Agent as a tools-off relay on Signal or Matrix. Not PicoClaw. | PicoClaw: no default-branch commits since 2026-08-19, two open CVEs with no patched version, README says not for production. |
| Computer control | Do not adopt a product. Build one sandbox image on PAI's own confirm gate and audit log; KasmVNC as the viewer. Cockpit as optional break-glass, off by default. | No candidate had a confirm gate plus audit log. bytebot and UI-TARS desktop are archived. |
| Cloud inference | Local by default, then a block list that never leaves the box, then Presidio masking forced on every cloud route, then an own vLLM pod over a tunnel. | RunPod has no confidential-computing offering; its host can read pod memory. Only the first two controls are guarantees. |
| Connectors | In-process, on `caldav` and `imapclient`; folders on the existing `sqlite-vec` + `fastembed`. | Credentials stay in the vault; no vendor cloud in the path. |
| Benchmarks | `llama-bench` for the engine, `guidellm` for the product path, raw JSON published. | Same engine PAI ships; comparable numbers. |

Rejected: `protectai/llm-guard` (archived), Wazuh (needs a manager), Zeek (too heavy), Composio and Nango (cloud or heavy), `llmperf` (archived).

## Phases, in order

### Phase 0: security fixes that cannot wait

- [x] Pin `ghcr.io/berriai/litellm` by image digest in `prototype/docker-compose.yml` and the root `docker-compose.yml`. Today it uses the floating `main-stable` tag. Confirm the chosen version against LiteLLM's own incident notes (2026-03 and 2026-10-21) before pinning.
- [x] Put LiteLLM on a Compose network with no default route out; allow only the provider hosts the owner has turned on.
- [x] Test: a compose lint test fails on any image without `@sha256:`.
- [x] Rewrite `prototype/setup-pai-vpn-gateway.sh`: remove `--advertise-exit-node`, `--advertise-routes`, `--ssh` and the MASQUERADE rule; stop piping `curl` to a root shell (use the distro package, pinned); accept a pre-auth key so a headless box does not block on login; add a teardown.
- [x] Remove the hardcoded `100.104.238.110` from `prototype/verify-vpn-tunnel.sh`; make it fail with a non-zero exit when a check fails.
- [x] Resolve two contradictions in the docs: PRD LAN-2 (no interception of other devices in MVP) against `docs/NETWORK-SECURITY-ENGINE.md`; and 1.1.1.1 DoH in the multi-shield doc against SPEC.md line 129.

Done 2026-11-25 on `claude/phase0-security-fixes`. LiteLLM is pinned to v1.108.17-lts by digest (keyless cosign signature verified); every other image is pinned too. LiteLLM sits on an internal network and reaches the internet only through an allowlist proxy (`prototype/egress`), checked live: direct egress fails, an allowlisted host answers, any other host gets 403. Also fixed: the root `docker-compose.yml` published the app and Ollama on all interfaces and carried a default vault key.

### Phase 1: owner login and device tokens (was item 7)

Blocks every later phase that exposes the app.

- [ ] First-boot creates one owner; passphrase hashed with Argon2id; no default password.
- [ ] Session cookie: HttpOnly, SameSite=Strict, Secure when served over TLS; server-side session table with expiry and revoke.
- [ ] Per-device tokens: one-time pairing code, stored hashed, listed and revocable on a Devices page.
- [ ] Every `/api/*` route except health and first-boot requires a session or device token. Test: each route returns 401 without one.
- [ ] Login, logout, pairing and revoke write to the audit chain.
- [ ] Rate-limit login and pairing attempts.

### Phase 2: private network, installable web app, QR pairing (was item 3)

- [ ] Web app manifest and service worker so it installs on a phone home screen (APP-1). State on 2026-11-25: a minimal manifest exists (`prototype/app/static/manifest.json`: name, colours, standalone) with no icons and no service worker, so phones will not offer to install it. No native app exists; `docs/superpowers/specs/2026-11-08-mobile-direction.md` recommends a Capacitor wrapper and is still marked decision pending. Its second open question (Tailscale as the default path) is now answered: yes.
- [ ] Publish the app on the overlay interface only (`tailscale serve`); never on the LAN or WAN interface.
- [ ] Pairing page shows a QR code holding the tailnet URL and a one-time device code from Phase 1 (APP-2).
- [ ] Tailscale account is the default; Headscale is the documented option (`PAI_LOGIN_SERVER`). Owner decision 2026-11-25. First version of the doc: `docs/PAI-MESH-VPN-SETUP.md`.
- [ ] Verify script checks: app unreachable from the LAN address, reachable from the tailnet address, 401 without a token.

### Phase 3: finish the M0 items marked "In progress" (was item 8)

- [ ] Run `prototype/app/run-e2e.sh`; record which of APP-3, APP-4, APP-5 and APP-12 the suite proves.
- [ ] Add missing tests, then code, for: first-boot interview resumes after a restart; the "what I will and won't do" page reflects the stored rules; a memory can be viewed, edited and deleted, and the delete is in the audit log.
- [ ] Update ROADMAP.md statuses from the evidence.

### Phase 4: data protection for cloud inference

- [ ] Presidio analyzer and anonymizer as Compose services; LiteLLM guardrail attached by PAI on every cloud route, not per request by the caller.
- [ ] Reversible placeholders; originals never leave the box. Test with a fake provider: the outbound body contains no seeded name, email, phone number or account number.
- [ ] Check streaming responses restore placeholders correctly; if not, disable streaming on cloud routes.
- [ ] Audit entry per cloud call: destination, model, masking result, bytes sent. No content unless `AUDIT_CONTENT=1`.
- [ ] "Own GPU pod" recipe: vLLM bound to localhost inside the pod, reached only through a tunnel, prompts on ephemeral disk. State plainly in the UI and docs that the pod host can read memory.
- [ ] Providers page shows a privacy level per destination: local, own pod (masked text only), ordinary API.
- [ ] State the limit in the docs and the Providers page: a prompt can be encrypted on the way to a rented GPU and on its disk, but the model has to read it in plain form in the GPU's memory, so the machine's operator can see it. Masking on the box before sending is the control that works today.
- [ ] Attested (TEE) providers: connector deferred. Recheck after the AMD SEV-SNP fixes due December 2026.

### Phase 5: host defence in the Docker prototype

- [ ] nftables default-drop; app and admin ports bound to localhost and the overlay interface.
- [ ] CrowdSec with the nftables bouncer; community blocklist enrolment off by default.
- [ ] Unbound as validating resolver and AdGuard Home for blocking, for the box's own DNS only (respects LAN-2).
- [ ] Lynis in CI and as a weekly scan; score shown on a Security page.
- [ ] Security page: firewall state, last scan, blocked attempts, devices paired.

### Phase 6: connectors and per-channel privacy (was item 9)

- [ ] Calendar (`caldav`), email (`imapclient`, read first), local folders (allowlisted paths, existing index). Each off by default.
- [ ] Credentials in the SQLCipher vault only. Writes (send, create, delete) go through the confirm gate.
- [ ] Privacy level shown for each connector and channel (APP-11).
- [ ] Check the `imapclient` licence before adding it; the API reported no SPDX id.

Owner decision 2026-11-25: automation hubs and a mail front end ship out of the box. This reverses the earlier rejection of Composio. All are off until the owner connects them.

- [ ] Hub connectors: Composio, Zapier, Make (cloud services) and n8n (self-hosted). One adapter interface; each exposes its actions to the router as tools. Every write goes through the confirm gate and the audit log.
- [ ] Privacy level per hub on the Connectors page: n8n on the box = local; Composio, Zapier and Make = cloud (the service sees the data and holds the account tokens). Their hosts are added to the outbound allowlist only while the hub is connected; block-list and masking rules apply to what is sent.
- [ ] n8n: its licence is not open source (GitHub reports no SPDX id; read the Sustainable Use License before shipping it inside a sold box). Safe default: connect to an n8n the owner runs, do not bundle it.
- [ ] Mail front end on local models: evaluate Mail-0/Zero (MIT, active 2026-11) and elie222/inbox-zero (active 2026-11; licence has no SPDX id, read it first). Point the chosen one's model setting at PAI's LiteLLM address so triage and drafting run on the box. Run a skillspector-style review and pin by digest before adding either.
- [ ] Both mail projects are built around Gmail and Outlook OAuth; confirm each works against plain IMAP before choosing, or keep the in-process `imapclient` path for other mailboxes.

### Phase 7: benchmarks (was item 10)

- [ ] `bench/run.sh`: `llama-bench` at a pinned commit, model sha256 and quant recorded; five runs, first dropped, median and spread.
- [ ] Product path: time to first token through LiteLLM and the app with `guidellm`.
- [ ] Run on the Dell and the Mac Pro; write raw JSON to `bench/results/`. Wall watts and noise need a smart plug and a sound meter (not owned yet).

### Phase 8: OS image (was item 6)

- [ ] Containerfile on Fedora bootc; app containers as Podman Quadlets; SELinux enforcing.
- [ ] greenboot-rs health checks; test a deliberately broken update and confirm it rolls back.
- [ ] Disk encryption with TPM2 + PIN (`systemd-cryptenroll`); confirm it survives an update and a rollback on a real Starter box.
- [ ] Installer built with `image-builder`, not the Anaconda ISO type.
- [ ] Decide ostree or composefs backend before deciding how app containers ship (composefs rejects logically bound images).
- [ ] Factory reset: `bootc install reset` leaves old data on disk, so add a secure wipe of the vault and keys.
- [ ] Signed install script for an existing Linux box; `os/ansible` stays as thin dev-box prep.
- [ ] usbguard, auditd feeding the audit chain, OpenSCAP baseline at build.

### Phase 9: store and hardware tiers (was items 1 and 12)

- [ ] PAI OS free and open source with a link to the repo; paid support optional (already in pai-store PR #1).
- [ ] Four hardware tiers at $500, $1,000, $3,000 and $5,000, each with listed upgrades. Shown as planned prices with a waitlist button; no checkout until units are sourced.
- [ ] Remove the "60% off" lines and struck-through list prices in `ProductDescription.tsx`, `AppleBoxConfigurator.tsx` and `how-it-works/page.tsx`; those list prices were never charged.
- [ ] Every tier page states that the network-security features are part of the free OS.
- [ ] Owner decision 2026-11-25: $3,000 = 64 GB, $5,000 = 128 GB. Part costs on 2026-10-31: 64 GB $1,753; 128 GB Pro $3,919; 32 GB box $829 to $1,133. Still a proposal, not yet confirmed: $500 = 16 GB entry box on a cheaper chassis than the current Starter; $1,000 = 32 GB Starter. Upgrades: memory, storage, GPU dock, second box.

### Later

- Chat channels (was item 4): Hermes Agent as a relay with all toolsets off, no vault key, bridge network, one allowlisted user. Add a thin `/v1/chat/completions` route over `reply_to()` so the router, confirm gate and audit log stay the only authority. Signal or Matrix with encryption required. Confirmations stay in the web app.
- Computer control (was item 5): one sandbox image (rootless Podman, read-only, capabilities dropped, pid, memory and CPU limits, no Docker socket), KasmVNC viewer on the overlay interface only, every action through the confirm gate. Owner decision 2026-11-25: both the owner's own shell and the assistant acting on the desktop. The owner prefers Rakazo (already run in the fleet as a browser sandbox appliance) as the remote desktop; vet it first (licence, upstream health, whether it can sit behind PAI's confirm gate and audit log) and fall back to the sandbox-plus-KasmVNC design if it fails.
- Suricata or Falco, opt-in, top tier only. Per-process egress control (Tetragon or OpenSnitch).

## Open questions for the owner

1. Specs for the $500 and $1,000 tiers (Phase 9); $3,000 = 64 GB and $5,000 = 128 GB are decided.
2. NVIDIA tier: enrol the Secure Boot key at the factory, or ship with Secure Boot off?
3. Gmail and Outlook: OAuth or app passwords at launch?
