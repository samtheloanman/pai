# PAI foundation design: request loop, schema map, endpoints, secure defaults

Status: proposed (2026-11-23). Applies to the PAI app (`prototype/app`) and the PAI OS image. Supersedes conflicting
details in SPEC.md where noted. Evidence for "today" claims: the owner's local review notes (`PAI foundation review/{data_layer,network_api}.md`, not in this repo)
(review of `main@f2b9e9f`) and PRs #7, #8, #9.

## 1. Requirements

**Functional (from PRD):** private chat and voice with local models; memory with view/forget (APP-5); onboarding
interview → rules → persona (APP-3/4); approval gate for risky actions (APP-12); opt-in masked cloud (PRIV-1..5);
hash-chained audit (AUD-1..4); owner login and device pairing (APP-2); CalDAV/IMAP/SMTP connectors (APP-6); Telegram
channel with privacy level (APP-7/11); Hermes terminal agent as a second UI; one onboarding definition rendered in web,
terminal (`pai setup`), headless seed file, later voice.

**Non-functional:**
- One household, 1–5 users, ≤10 devices. One box. No horizontal scale. Latency matters (voice), throughput does not.
- No public ports. Works offline. Cloud is opt-in, masked, audited.
- Survives power loss mid-update (OS-10 A/B rollback); vault readable by the previous app version.
- Every security decision is enforced server-side and at the network layer, never only in the UI.

**Constraints:** Python/FastAPI app, SQLCipher, llama.cpp + LiteLLM + Speaches, Fedora bootc + Quadlets (target),
AGPL-3.0, very small team.

**Assumptions:** owner is non-technical; LAN is not trusted (other household devices, guests, IoT); the owner's own
browser is not trusted to be free of malicious tabs (DNS rebinding / CSRF are in scope).

## 2. High-level design

```
            LAN / tailnet                          ┌─────────────── PAI box ────────────────────────────────────┐
 browser ─┐  https://pai.local (443)               │ Z0 host: nftables default-deny, avahi, tailscaled, sshd*    │
 phone   ─┼──────────────────────────────────────▶ │  Caddy (TLS internal CA, Host allowlist, size/rate limits)  │
 pai CLI ─┘  (pai setup / pai doctor, Hermes TUI)  │     │                                                        │
                                                   │ Z1/Z2 core (internal network, no internet)                 │
                                                   │  PAI API ── Policy engine ── Action gate ── Audit writer   │
                                                   │     │  │          │                                        │
                                                   │     │  └─ Hermes gateway (device token: chat+propose)      │
                                                   │     │  └─ Connectors broker (IMAP/SMTP/CalDAV, SSRF guard) │
                                                   │     │  └─ Telegram poller (long-poll, owner chat_id only)  │
                                                   │     ▼                                                      │
                                                   │ Z3 inference (internal): LiteLLM ─▶ llama.cpp, Speaches    │
                                                   │     │ (cloud only via proxy, only after policy approval)   │
                                                   │ Z4 egress: one proxy, FQDN allowlist ──────────────────────┼─▶ internet
                                                   │ Storage: pai.db | secrets.db | audit.db (SQLCipher)        │
                                                   └────────────────────────────────────────────────────────────┘
 * sshd on tailscale0 only, opt-in
```

Two UIs, one API: the web UI and the terminal (`pai` CLI + Hermes TUI) are both clients of `/api/v1`. Neither has a
private back door. Hermes never holds the LiteLLM master key.

## 3. The request loop

Every inbound turn — web chat, voice, Telegram message, Hermes prompt — goes through the same pipeline. One function
owns it (`pai/loop.py`, extracted from `main.reply_to`). Channels only adapt input/output.

```
 1 ingress      channel adapter → Envelope{user, device, channel, privacy_level, text|audio, request_id}
 2 authn/authz  session cookie | device token | setup token → scopes; reject before any work
 3 limits       size cap (text 32k chars — PR #8; audio 25 MB / 120 s), per-device rate limit
 4 normalize    STT for audio (local only); strip control chars; mark channel text UNTRUSTED
 5 route        rules tier → embeddings tier → decide model (pai/routing.py); only the rules tier may remember/act
 6 context      persona + rules + top-k memories filtered by channel policy (allow_memory_read)
 7 policy       local by default. Cloud only if: cloud_enabled AND request.cloud AND channel allows AND
                blocks.allowed_for_cloud(payload) AND size ≤ cap  → else stay local (fail closed)
 8 mask         reversible masking of emails/phones/names (pai/masking.py) for cloud payloads only
 9 model call   app → LiteLLM (app-held key) → llama.cpp | proxy → allowlisted cloud
10 unmask       restore placeholders in the reply
11 tool intents model output parsed into Proposals; never executed inline
12 action gate  low-risk → may auto-run if policy allows; send/delete/spend/system → pending, needs owner
                session + step-up; Hermes/Telegram can propose, never confirm
13 memory write only via rules tier or confirmed action; provenance (source, channel_id) recorded
14 audit        append entry per step that matters (route, model_call, outbound, action_*, memory_*);
                audit failure on an outbound path = abort, nothing sent (existing invariant)
15 egress       reply to channel; TTS locally for voice
```

Error handling and retries:
- Local model errors: one retry with backoff, then a plain error to the user; never silently fall back to cloud.
- Cloud errors: no retry with a different provider unless the owner configured a fallback list; each attempt is a
  separate `outbound` audit entry.
- Connector sync: exponential backoff, cursor stored in `connectors.sync_cursor`; failures surface in `pai doctor`.
- Action execution is idempotent per `action.id` (status transitions `pending→confirmed→done|failed` are a single
  `UPDATE … WHERE status='pending'`), so double-clicks and retries cannot run twice.

Onboarding loop (same engine, different source of truth):
```
onboarding schema (YAML, versioned) ─▶ /api/v1/setup/* ─▶ renderers: web wizard | pai setup (TUI) | seed file | voice
                                      each answer validated server-side, stored in profile, audited as config_changed
```
The schema is the only place questions, validation and order live. Renderers carry no logic.

## 4. Schema map

### 4.1 Storage files and keys

| File | Holds | Opened by | Key |
|---|---|---|---|
| `pai.db` | profile, memories (+FTS, vectors), rules, actions, settings, users/devices/sessions, channels, connectors (no secrets), consents, agent sessions | app | HKDF(master, "vault") raw key |
| `secrets.db` | provider API keys, Telegram bot token, IMAP/SMTP/CalDAV passwords, OAuth refresh tokens | `pai/secrets.py` only; never searched, never in prompts | HKDF(master, "secrets") |
| `audit.db` | hash-chained entries, checkpoints | `pai/audit.py` only | HKDF(master, "audit") |
| outside DB | `DATA_DIR/files/` (file tools root), `maildir/`, model caches | — | disk encryption (LUKS + TPM) |

Master key: TPM-sealed systemd credential (`systemd-creds --with-key=tpm2`), recovery code printed once at setup.
Raw 256-bit keys, no per-open PBKDF2 (PR #9). Audit head hash and entry count are also stored in `pai.db`
`vault_meta` (later a TPM NV counter) so truncation or rollback of `audit.db` fails verification.

### 4.2 Feature → data → endpoint → zone

| Feature | Tables (file) | v1 endpoints | Zone |
|---|---|---|---|
| Onboarding | `profile`, `rules`, `onboarding_profile`, `agent_personas`, `skills_and_tools` (pai) | `/setup/*`, `/rules` | core |
| Login / pairing | `users`, `devices`, `pairing_tokens`, `sessions` (pai) | `/auth/*`, `/devices/*` | core |
| Chat / voice | `memories*`, `agent_sessions`, `agent_turns`, `voice_transcripts` (pai) | `/chat`, `/voice/*` | core → inference |
| Memory | `memories`, `memories_fts`, `memories_vec`, `tombstones` (pai) | `/memories` | core |
| Approvals | `actions` (+requested_by, decided_by, purged_at) (pai) | `/actions` | core |
| Cloud | `providers` (no key), `settings`, `consents` (pai); key in `secrets` | `/providers`, `/egress` | core → egress |
| Connectors | `connectors` (pai); credentials in `secrets` | `/connectors` | connectors broker → egress |
| Telegram | `channels`, `channel_identities` (pai); bot token in `secrets` | internal socket only | poller → egress |
| Hermes | `devices` (scoped token), `agent_sessions`, `skill_runs` (pai) | `/llm/chat/completions`, `/chat`, `/actions` (propose) | core |
| Audit | `entries`, `checkpoints` (audit) | `/audit` | core |
| Bench | `bench_results` (pai) | `/bench` (admin) | core |

DDL for the new tables is drafted in the local data-layer review notes (§5) and lands with Wave 2 migrations. Rules for every new table:
- `owner_id`/`user_id` and `created_at` on anything personal (household-ready).
- Secrets are referenced by `secret_ref` (an id in `secrets.db`), never stored in `pai.db`.
- Tokens are stored as SHA-256 hashes, never raw.
- One `forget(kind, ref)` function deletes base row + FTS (followed by `optimize`) + vector + derived snippets, and writes
  a tombstone. Test: after forget, the decrypted DB contains no trace of the text.
- Migrations stay additive; app vN must open vN+1 read-only instead of refusing (OS-10).
- Retention: `actions.payload` nulled 30 days after decision; `agent_turns` and `voice_transcripts` retention set at
  onboarding (default 90 days); audio is never stored.

## 5. Endpoint organization

All routes move under `/api/v1`, grouped by resource. One router module per group. Old `/api/*` paths are kept for one
release as aliases, then removed.

| Group | Routes | Purpose |
|---|---|---|
| `health` | `GET /health` | liveness only, no data |
| `setup` | `GET/POST /setup/questions`, `POST /setup/answers`, `POST /setup/rules/draft`, `POST /setup/compile`, `POST /setup/owner` | onboarding engine (§3); pre-owner requires setup token |
| `auth` | `POST /auth/login`, `POST /auth/logout`, `POST /auth/step-up`, `GET /auth/me` | sessions, passkey/PIN step-up |
| `devices` | `POST /devices/pairing-codes`, `POST /devices/pair`, `GET /devices`, `DELETE /devices/{id}` | pairing, revocation |
| `chat` | `POST /chat`, `POST /voice/transcribe`, `POST /voice/speak`, `POST /voice/turn`, `POST /voice/offer` | conversation |
| `memories` | `GET /memories`, `POST /memories/{id}/forget` (creates a proposal) | view/forget |
| `rules` | `GET /rules`, `PUT /rules` | constitution |
| `actions` | `GET /actions`, `POST /actions` (propose), `POST /actions/{id}/confirm`, `POST /actions/{id}/reject` | approval gate |
| `tools` | `GET /tools/files`, `GET /tools/files/content`, `GET /tools/mail` | read-only views; writes are proposals |
| `providers` | `GET /providers`, `PUT /providers/{name}`, `PUT /providers/cloud` | cloud opt-in |
| `egress` | `GET /egress/allowlist`, `PUT /egress/allowlist` | network policy |
| `connectors` | `GET/POST/DELETE /connectors`, `POST /connectors/{id}/test` | IMAP/SMTP/CalDAV |
| `audit` | `GET /audit`, `POST /audit/verify` | log + verify (POST: it writes a checkpoint) |
| `llm` | `POST /llm/chat/completions` | OpenAI-compatible shim for Hermes; runs the full loop |
| internal | Unix socket: `/channels/telegram/ingest`, LAN Guardian events | never on TCP |

API conventions:
- JSON only; reject requests without `Content-Type: application/json` (closes typeless-body CSRF).
- No state change on GET. Every state-changing route returns the audit entry id.
- Errors: `{"error": {"code": "...", "message": "..."}}`; never echo exception text or upstream bodies.
- Pagination: `?limit=` (max 500) and `?before=<id>` cursors.
- IDs: random (UUIDv7 or 128-bit), never sequential, for anything exposed.

### Auth matrix

| Route group | unauth | setup token | device `chat` | device `propose` | owner session | owner + step-up |
|---|---|---|---|---|---|---|
| health | ✓ | | | | | |
| setup | | ✓ (until owner exists) | | | ✓ re-run | |
| auth/me, logout | | | ✓ | ✓ | ✓ | |
| chat, voice, llm | | | ✓ | | ✓ | |
| memories (read), rules (read), tools (read) | | | ✓ | | ✓ | |
| memories forget, actions propose | | | | ✓ | ✓ | |
| actions confirm (low risk) | | | | | ✓ | |
| actions confirm (send/delete/spend/system) | | | | | | ✓ |
| rules write, onboarding reset | | | | | | ✓ |
| providers, cloud, egress, connectors write | | | | | | ✓ |
| devices pair/revoke | | | | | | ✓ |
| audit | | | | | ✓ | |

Hermes: device token with `chat` + `propose`. Telegram: no token; ingested over the Unix socket, mapped to the owner via
`channel_identities`, treated as `chat` + `propose` at its channel's privacy level.

## 6. Secure defaults

### 6.1 Network

| Setting | Default | Why |
|---|---|---|
| Listening sockets | Caddy on LAN + tailscale0 :443 only; app on internal network; nothing on 0.0.0.0 in dev compose | OS-5 (reworded: LAN/overlay only, behind TLS + auth, never public) |
| Container networks | `internal: true` for core and inference; only the egress proxy joins a routable network | LiteLLM is not a chokepoint today; containers reach the internet directly |
| Host firewall | nftables `forward` and `output` policy drop; explicit allows per flow; drops logged → audit `egress_denied` | default-deny egress |
| Egress allowlist | provider FQDNs only when that provider is enabled; connector hosts as the owner adds them; `api.telegram.org` when Telegram is on | every allowlist change is an audited, step-up action |
| Model downloads | one-shot install/update service; inference containers never get internet | |
| Names | mDNS `pai.local` for discovery only; trust anchored by the cert fingerprint in the pairing QR | mDNS is spoofable |
| TLS | Caddy `tls internal` CA; HTTPS required (browser mic needs it); remote via `tailscale serve`, never funnel | |
| Tailscale | ACL `owner → tag:pai:443`; no exit node, no subnet routes, no blanket FORWARD accept by default | today's VPN script exposes the whole LAN |
| Inbound channels | none: Telegram long-polls outward; no webhooks | |
| Inference services | llama.cpp `--api-key`, Speaches UI off, reachable only from LiteLLM | |

### 6.2 Application

| Setting | Default |
|---|---|
| Host allowlist | `pai.local`, `localhost`, `127.0.0.1`, `<box>.<tailnet>.ts.net` (app middleware **and** Caddy) — blocks DNS rebinding |
| CSRF | `Origin` in allowlist **and** `X-PAI-CSRF` header bound to session on every non-GET |
| Session cookie | `__Host-pai_session; Secure; HttpOnly; SameSite=Strict; Path=/`; 12 h idle, 7 d absolute; server-side table |
| Setup token | 128-bit, single use, 30 min, URL fragment only, regenerated each boot until an owner exists |
| Pairing code | 128-bit, 5 min, single use, max 3 outstanding, confirmed on the owner's screen |
| Step-up | passkey or PIN within 5 min for send/delete/spend/system, rules, providers, egress, devices |
| Headers | `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; object-src 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy: microphone=(self)` |
| Limits | body 1 MB (JSON), 25 MB (audio); cloud-check input 32k chars; per-device 60 req/min, 5 confirms/min |
| Debug surfaces | `/docs`, `/openapi.json`, `/redoc` off unless `PAI_DEBUG=1` on localhost; `/api/route` removed from prod |
| Provider base URL | https only, host on allowlist, resolved IP not private/loopback/link-local |
| Connector hosts | SSRF guard (block loopback, link-local, metadata, container subnets; RFC1918 only if owner ticks "on my LAN"); IP pinned per connection; TLS verify mandatory |
| Logging | no request bodies, no query strings with paths, no model/upstream error bodies; uvicorn access log path-only |
| Untrusted input | Telegram, mail, calendar and web text are tagged untrusted; they can never cause a memory write or action confirm by themselves |

### 6.3 Data

| Setting | Default |
|---|---|
| SQLCipher | raw 256-bit keys (PR #9); `cipher_memory_security=ON`; `secure_delete=ON`; `temp_store=MEMORY`; WAL with `wal_checkpoint(TRUNCATE)` after forget |
| Keys | TPM-sealed master → HKDF subkeys per file; recovery code; `key_version` in `vault_meta`; rotation via `PRAGMA rekey` |
| Vault key delivery | systemd credential / Compose secret / Keychain; never env or `.env` (PR #7) |
| File tools | root `DATA_DIR/files`; DB, WAL, key, `.env` files refused (PR #8) |
| Audit | `AUDIT_CONTENT=0` by default (metadata only); head hash mirrored outside `audit.db`; verify is POST |
| Backups | restic, encrypted with the backup subkey, before every OS update (OS-10) and nightly; restore tested by `pai doctor` |

## 7. Trade-offs

| Decision | Chosen | Alternative | Why |
|---|---|---|---|
| Masking location | in the app's loop | in a LiteLLM callback | app already has the policy context (channel, rules); LiteLLM is kept unreachable to anyone else, so the bypass is closed by network design instead |
| Hermes integration | device token + `/llm` shim | LiteLLM virtual key | shim keeps masking, blocks and audit on every Hermes call; virtual key needs a LiteLLM DB and still bypasses masking |
| Three DB files | yes | one DB with tables | separate keys limit blast radius; `secrets.db` can never be hit by search or a prompt bug |
| Raw vs passphrase keys | raw for 256-bit keys | PBKDF2 everywhere | 900× faster opens, no security loss for random keys (PR #9) |
| Telegram | long-poll | webhook | no inbound port; costs a persistent outbound connection |
| TLS on LAN | local CA + QR pin | plain HTTP on LAN | mic access and cookie `Secure` need HTTPS; cost is a one-time trust step at pairing |
| Auth for MVP | passphrase + PIN, passkey next | passkey only | passkeys on `pai.local` with a private CA are awkward on some phones; PIN step-up still protects approvals |

## 8. Delivery order

1. **Wave 1.5 (small, before any LAN exposure):** Host allowlist, Origin + custom-header CSRF, JSON-only bodies,
   security headers, debug routes off, provider URL validation, memory delete via proposal, POST verify, audit head
   mirrored in `pai.db`, request limits, temp_store/memory_security pragmas.
2. **Wave 2:** `/api/v1` routers; `users/devices/pairing_tokens/sessions`; setup token + pairing QR; `secrets.db` and
   migration of `providers.key`/`connections_ingress.secret_key`; onboarding schema + `pai setup`; Hermes shim + token;
   forget completeness; connectors broker with SSRF guard.
3. **Wave 3 (bootc OS):** Quadlets with internal networks, nftables default-deny, egress proxy, Caddy local CA,
   TPM-sealed master key, restic, model-fetch one-shot, Tailscale ACL defaults, CI test "no listening socket on a
   non-allowed interface" (PRD.md:208).

## 9. Revisit as it grows

- Multi-user households: per-user memory partitions and per-user audit views (the `owner_id` columns are the hook).
- More than one box (mesh): per-box keys, replicated tombstones, Headscale policy.
- Long-lived SQLite connections or a single writer thread if concurrency rises (not needed after PR #9).
- Moving masking into a dedicated sidecar if other clients ever need cloud access without the app.
- Replacing in-memory rate limits with a persisted limiter if multiple app workers are added.

## 10. Decisions needed from the owner

1. Reword PRD OS-5 to "LAN and overlay interfaces only, behind TLS and auth; never a public interface".
2. Default retention for chat turns and voice transcripts (proposed 90 days).
3. Whether Telegram may approve low-risk actions inline (proposed: notify only for MVP).
