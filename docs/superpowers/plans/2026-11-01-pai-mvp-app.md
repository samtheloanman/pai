# PAI MVP App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the Docker prototype into the MVP PAI app: encrypted vault with hybrid search, tiered request routing, a hash-chained audit trail, a confirm gate for risky actions, opt-in cloud providers with hard blocks, and the UI for all of it.

**Architecture:** Split `prototype/app/main.py` into a small `pai` package (store, vault, routing, audit, actions, providers) with FastAPI routes staying in `main.py`. All model calls still go through LiteLLM; the app owns routing, auditing and the confirm gate. The React front end in `prototype/web` gains Activity, Approvals and Providers views.

**Tech Stack:** Python 3.12, FastAPI, SQLCipher (`sqlcipher3-binary`), SQLite FTS5, sqlite-vec, fastembed (all-MiniLM-L6-v2), LiteLLM, llama.cpp server, React 19 + @assistant-ui/react, Vite, pytest, vitest.

**Spec:** `PRD.md` v0.2 (sections 5.2, 5.4–5.9, OS-10). Out of scope here: the bootc OS image (OS-1, OS-2, OS-11, OS-12), hardware, Telegram/email channels (APP-7/8), LAN awareness, learning beyond memory (LEARN-2..4), Presidio masking (PRIV-2, a later plan). Each gets its own plan.

## Global Constraints

- Nothing binds a public interface: compose ports stay `127.0.0.1:` (OS-5).
- No cloud provider by default; cloud only with the owner's own key and `cloud_enabled = true` (ROUTE-3, PRIV-1).
- Secrets, card numbers and the owner's off-limits topics never go to a cloud model (PRIV-3).
- Any send, delete, spend or system change needs an explicit owner confirm, whatever a model decides (ROUTE-5, APP-12).
- Audit entries are metadata only unless `AUDIT_CONTENT=1` (AUD-2); the audit log is a separate encrypted file (AUD-3).
- Schema changes are additive only (add tables/columns, never rename or drop) (OS-10).
- Pin every new dependency to an exact version in `requirements.txt` / `package.json`.
- Copy follows `docs/BRAND-CLAIMS.md`: no speed numbers in the UI.
- Run tests: back end `cd prototype/app && .venv/bin/pytest -q`; front end `cd prototype/web && npm test`.

## Review Focus

- Wrong or missing vault key on start → app exits with a clear message, never creates a second empty vault (Task 2 test `test_wrong_key_refuses`).
- Two requests writing audit entries at once → chain stays valid (Task 4 test `test_concurrent_writes_keep_chain`).
- Cloud key saved but cloud switch off → no cloud call is ever made (Task 6 test `test_key_without_switch_stays_local`).
- An action confirmed twice, or confirmed after it expired → executes at most once (Task 5 test `test_confirm_is_idempotent_and_expires`).
- Very long input (50k chars) to the router/embedder → truncated, no crash (Task 3 test `test_long_input_is_truncated`).

---

### Task 1: Package split and schema versioning (OS-10)

**Files:**
- Create: `prototype/app/pai/__init__.py`, `prototype/app/pai/store.py`
- Modify: `prototype/app/main.py` (use `store.connect` instead of `db()`), `prototype/app/Dockerfile` (copy `pai/`)
- Test: `prototype/app/tests/test_store.py`; move existing `test_main.py` to `prototype/app/tests/test_main.py`

**Interfaces:**
- Produces: `SCHEMA_VERSION: int = 2`; `class SchemaTooNew(Exception)`; `connect(path: str, key: str | None = None) -> sqlite3.Connection` (applies migrations up to `SCHEMA_VERSION`, raises `SchemaTooNew` if the file's `user_version` is higher); `MIGRATIONS: list[str]` (index = version - 1).

- [ ] **Step 1: Failing tests** in `tests/test_store.py`:

```python
def test_fresh_db_is_at_current_version(tmp_path):
    con = store.connect(str(tmp_path / "a.db"))
    assert con.execute("pragma user_version").fetchone()[0] == store.SCHEMA_VERSION

def test_newer_schema_is_refused(tmp_path):
    p = str(tmp_path / "a.db"); con = store.connect(p)
    con.execute(f"pragma user_version = {store.SCHEMA_VERSION + 1}"); con.close()
    with pytest.raises(store.SchemaTooNew):
        store.connect(p)

def test_migrations_are_additive_only():
    for sql in store.MIGRATIONS:
        assert not re.search(r"\b(drop|rename)\b", sql, re.I)
```

- [ ] **Step 2:** `pytest tests/test_store.py -q` → FAIL (module missing).
- [ ] **Step 3:** Implement `store.py`. Version 1 = the existing `profile`, `memories`, `rules` tables. Version 2 adds `memories_fts` (FTS5 over `memories.text`, kept in sync by triggers) and `actions`, `providers` tables (columns defined in Tasks 5 and 6; create them here).
- [ ] **Step 4:** All tests (old + new) pass: `pytest -q` → 13+ passed.
- [ ] **Step 5:** Commit `refactor: pai package with versioned additive migrations`.

### Task 2: Encrypted vault and hybrid search (VAULT-1)

**Files:**
- Create: `prototype/app/pai/vault.py`
- Modify: `prototype/app/pai/store.py` (use SQLCipher when `key` is set), `main.py` (`recall` → `vault.search`), `requirements.txt` (+ `sqlcipher3-binary`, `sqlite-vec`, exact versions), `docker-compose.yml` (+ `PAI_VAULT_KEY` from `.env`), `.env.example`
- Test: `prototype/app/tests/test_vault.py`

**Interfaces:**
- Consumes: `store.connect(path, key)`.
- Produces: `class VaultKeyError(Exception)`; `search(con, query: str, limit: int = 5, embed: Callable[[str], list[float]] | None = None) -> list[str]` (FTS5 BM25 results merged with vector results when `embed` is given, reciprocal-rank fusion, de-duplicated); `add_memory(con, text: str, embed=None) -> int`.

- [ ] **Step 1: Failing tests:**

```python
def test_file_is_unreadable_without_key(tmp_path):
    p = str(tmp_path / "v.db"); store.connect(p, key="k1").close()
    with pytest.raises(vault.VaultKeyError):
        store.connect(p, key=None)

def test_wrong_key_refuses(tmp_path):
    p = str(tmp_path / "v.db"); store.connect(p, key="k1").close()
    with pytest.raises(vault.VaultKeyError):
        store.connect(p, key="k2")
    assert len(list(tmp_path.iterdir())) == 1   # no second vault created

def test_keyword_search_finds_exact_terms(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    for t in ["invoice 4471 from Acme", "dentist on Fridays", "Jo prefers calls before 11"]:
        vault.add_memory(con, t)
    assert vault.search(con, "4471")[0] == "invoice 4471 from Acme"

def test_hybrid_merges_vector_hits(tmp_path):
    con = store.connect(str(tmp_path / "v.db"), key="k")
    fake = lambda s: [1.0, 0.0] if "tooth" in s or "dentist" in s else [0.0, 1.0]
    vault.add_memory(con, "dentist on Fridays", embed=fake)
    vault.add_memory(con, "oat latte", embed=fake)
    assert vault.search(con, "tooth pain", embed=fake)[0] == "dentist on Fridays"
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. SQLCipher: `PRAGMA key` then a probe read; translate `DatabaseError: file is not a database` into `VaultKeyError`. Vectors in a sqlite-vec `vec0` table keyed by memory id. App startup fails fast with the `VaultKeyError` message when `PAI_VAULT_KEY` is wrong.
- [ ] **Step 4:** `pytest -q` → all pass; `docker compose --profile local up -d --build app` and `curl -s localhost:8088/api/health` → `{"ok":true}`.
- [ ] **Step 5:** Commit `feat: SQLCipher vault with FTS5 + vector hybrid search`.

### Task 3: Tiered routing (ROUTE-4, ROUTE-6)

**Files:**
- Create: `prototype/app/pai/routing.py`, `prototype/app/pai/embed.py`, `bench/route_cases.jsonl` (≥ 40 labelled requests), `bench/route_bench.py`
- Modify: `main.py` (`reply_to` dispatches on the route), `litellm.local.yaml` (+ `pai-decide` alias → same llama.cpp server), `docker-compose.yml` (llama.cpp `--parallel 2` so the decision call gets its own slot)
- Test: `prototype/app/tests/test_routing.py`

**Interfaces:**
- Produces: `ROUTES = ("remember", "memory_query", "calendar", "email", "action", "chat")`; `@dataclass Route(name: str, tier: int, score: float)` (tier 1 rules, 2 embedding, 3 model); `async def route(text: str, embed=None, decide=None) -> Route`; `EMBED_THRESHOLD = 0.55` (initial, tuned by the bench); `MAX_CHARS = 4000`; `embed.embed(text: str) -> list[float]` (fastembed `sentence-transformers/all-MiniLM-L6-v2`, model cached under `DATA_DIR/models`).

- [ ] **Step 1: Failing tests:**

```python
async def test_rule_tier_catches_remember():
    r = await routing.route("Remember that rent is due on the 1st")
    assert (r.name, r.tier) == ("remember", 1)

async def test_embedding_tier_used_when_confident():
    r = await routing.route("what's on my schedule tomorrow", embed=fake_embed_calendar)
    assert (r.name, r.tier) == ("calendar", 2)

async def test_model_tier_only_when_embedding_unsure():
    calls = []
    async def decide(t): calls.append(t); return "chat", 0.8
    r = await routing.route("hmm", embed=lambda s: [0.0] * 384, decide=decide)
    assert r.tier == 3 and len(calls) == 1

async def test_long_input_is_truncated():
    seen = []
    await routing.route("x" * 50_000, embed=lambda s: seen.append(len(s)) or [0.0] * 384, decide=fake_decide)
    assert max(seen) <= routing.MAX_CHARS
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement. Tier 2 compares against 3–5 example phrases per route (cosine); tier 3 calls LiteLLM model `pai-decide` with a prompt that must return JSON `{"route": <one of ROUTES>, "p": <0..1>}`; invalid JSON → `Route("chat", 3, 0.0)`.
- [ ] **Step 4:** `pytest -q` → pass. Then `python bench/route_bench.py --base http://localhost:8088` prints accuracy per tier and p50/p95 added latency; save output to `bench/results/route-<date>.json`. No accuracy target yet (ROUTE-6 sets it from this run).
- [ ] **Step 5:** Commit `feat: tiered routing (rules, embeddings, decision model) + route bench`.

### Task 4: Audit trail (AUD-1, AUD-2, AUD-3, AUD-5)

**Files:**
- Create: `prototype/app/pai/audit.py`
- Modify: `main.py` (every `llm()`, transcription, speech call, route decision and memory change calls `audit.record`), `docker-compose.yml` (`AUDIT_CONTENT` default `0`)
- Test: `prototype/app/tests/test_audit.py`

**Interfaces:**
- Produces: `record(kind: str, **fields) -> int` (kinds: `model_call`, `route`, `action_proposed`, `action_confirmed`, `action_rejected`, `memory_added`, `memory_deleted`, `outbound`, `config_changed`); `verify() -> int | None` (id of first broken entry, `None` if intact); `entries(limit: int = 100, kind: str | None = None) -> list[dict]`. Stored in `DATA_DIR/audit.db` (SQLCipher, same key). Field names: `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `duration_ms`, `pai.route`, `pai.provider`.

- [ ] **Step 1: Failing tests:**

```python
def test_chain_verifies_and_detects_edits(audit_db):
    for i in range(3): audit.record("route", **{"pai.route": "chat"})
    assert audit.verify() is None
    audit._con().execute("update entries set fields = '{}' where id = 2")
    assert audit.verify() == 2

def test_content_not_stored_by_default(audit_db):
    audit.record("model_call", prompt="secret text", **{"gen_ai.request.model": "pai-chat"})
    assert "secret text" not in json.dumps(audit.entries())

def test_concurrent_writes_keep_chain(audit_db):
    threads = [threading.Thread(target=audit.record, args=("route",)) for _ in range(20)]
    [t.start() for t in threads]; [t.join() for t in threads]
    assert audit.verify() is None and len(audit.entries(limit=50)) == 20

def test_chat_call_writes_one_model_call_entry(client, mock_litellm): ...
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement: each row stores `id, ts, kind, fields (json), prev_hash, hash = sha256(prev_hash + ts + kind + fields)`; writes serialized with a process lock and `BEGIN IMMEDIATE`. Content fields (`prompt`, `reply`, `text`) are dropped unless `AUDIT_CONTENT=1`. Add `GET /api/activity?kind=` and `GET /api/activity/verify`.
- [ ] **Step 4:** `pytest -q` → pass.
- [ ] **Step 5:** Commit `feat: hash-chained audit trail and activity API`.

### Task 5: Confirm gate for risky actions (ROUTE-5, APP-12)

**Files:**
- Create: `prototype/app/pai/actions.py`
- Modify: `main.py` (route `action` → propose, never execute; endpoints below)
- Test: `prototype/app/tests/test_actions.py`

**Interfaces:**
- Consumes: `audit.record`.
- Produces: `RISKY = {"send", "delete", "spend", "system"}`; `propose(kind: str, summary: str, payload: dict, ttl_s: int = 900) -> str` (id); `confirm(action_id: str, executor: Callable[[dict], Any]) -> dict` (runs executor at most once; `{"status": "done" | "expired" | "already_done" | "rejected"}`); `reject(action_id: str) -> None`; `pending() -> list[dict]`. Endpoints: `GET /api/actions`, `POST /api/actions/{id}/confirm`, `POST /api/actions/{id}/reject`. MVP executor registry has one safe built-in: `delete_memory`.

- [ ] **Step 1: Failing tests:**

```python
def test_risky_action_does_not_run_on_propose():
    ran = []
    aid = actions.propose("delete", "Delete memory 3", {"memory_id": 3})
    assert ran == [] and actions.pending()[0]["id"] == aid

def test_confirm_is_idempotent_and_expires(monkeypatch):
    ran = []
    aid = actions.propose("delete", "x", {}, ttl_s=60)
    assert actions.confirm(aid, lambda p: ran.append(1))["status"] == "done"
    assert actions.confirm(aid, lambda p: ran.append(1))["status"] == "already_done"
    old = actions.propose("delete", "y", {}, ttl_s=60)
    monkeypatch.setattr(actions, "now", lambda: time.time() + 61)
    assert actions.confirm(old, lambda p: ran.append(1))["status"] == "expired"
    assert ran == [1]

def test_confirm_and_reject_are_audited(): ...
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement on the `actions` table from Task 1. **Step 4:** `pytest -q` → pass.
- [ ] **Step 5:** Commit `feat: confirm gate for risky actions`.

### Task 6: Providers, cloud opt-in and hard blocks (ROUTE-2, ROUTE-3, PRIV-1, PRIV-3, PRIV-4, PRIV-5)

**Files:**
- Create: `prototype/app/pai/providers.py`, `prototype/app/pai/blocks.py`
- Modify: `main.py` (chat may use `pai-cloud` only via `providers.choose_model`), `docker-compose.yml` (app writes `litellm.generated.yaml` into a shared volume; litellm reads it; restart litellm on change), `litellm.local.yaml` stays the fallback
- Test: `prototype/app/tests/test_providers.py`, `prototype/app/tests/test_blocks.py`

**Interfaces:**
- Produces: `PROVIDERS = {"openrouter": "openrouter/", "huggingface": "huggingface/", "nvidia": "nvidia_nim/", "ollama": "ollama/", "lmstudio": "lm_studio/"}`; `save_key(name: str, key: str) -> None` (stored in the encrypted vault `providers` table); `set_cloud_enabled(on: bool) -> None`; `render_litellm_config() -> str` (YAML; cloud entries only for providers with a key); `choose_model(text: str, route: Route, want_cloud: bool = False) -> str` returns `"pai-chat"` unless `want_cloud` AND cloud enabled AND `blocks.allowed_for_cloud(text, off_limits)[0]`; `blocks.allowed_for_cloud(text: str, off_limits: list[str]) -> tuple[bool, str]` (reason). Blocks: API-key patterns (`sk-`, `ghp_`, `AKIA`, generic 32+ char hex/base64 tokens), Luhn-valid 13–19 digit numbers, US SSN pattern, and any off-limits phrase from the profile. Every cloud call → `audit.record("outbound", **{"pai.provider": ..., "chars": len(text)})`.

- [ ] **Step 1: Failing tests:**

```python
def test_key_without_switch_stays_local(vault):
    providers.save_key("openrouter", "sk-or-test")
    assert providers.choose_model("hello", Route("chat", 2, .9), want_cloud=True) == "pai-chat"

def test_card_number_blocks_cloud():
    ok, why = blocks.allowed_for_cloud("my card is 4111 1111 1111 1111", [])
    assert not ok and "card" in why

def test_off_limits_topic_blocks_cloud():
    assert not blocks.allowed_for_cloud("tell me about my divorce", ["divorce"])[0]

def test_rendered_config_has_only_keyed_providers(vault):
    providers.save_key("nvidia", "nvapi-test")
    cfg = yaml.safe_load(providers.render_litellm_config())
    names = {m["litellm_params"]["model"].split("/")[0] for m in cfg["model_list"]}
    assert "nvidia_nim" in names and "openrouter" not in names
    assert "nvapi-test" not in providers.render_litellm_config()  # key passed via env reference, never inlined
```

- [ ] **Step 2:** Run → FAIL. **Step 3:** Implement. Keys reach LiteLLM through environment variables written to a 0600 env file, never inlined in YAML. **Step 4:** `pytest -q` → pass.
- [ ] **Step 5:** Commit `feat: opt-in cloud providers with hard blocks and outbound audit`.

### Task 7: Front end: Activity, Approvals, Providers (AUD-4, PRIV-1)

**Files:**
- Create: `prototype/web/src/Activity.jsx`, `prototype/web/src/Approvals.jsx`, `prototype/web/src/Providers.jsx`, `prototype/web/src/format.js`, `prototype/web/src/format.test.js`
- Modify: `prototype/web/src/App.jsx` (tabs: Chat, Approvals (badge with pending count), Activity, Memory, Rules, Setup, Providers), `styles.css`

**Interfaces:**
- Consumes: `/api/activity`, `/api/activity/verify`, `/api/actions*`, `/api/providers` (GET list without keys, PUT `{name, key}`, PUT `{cloud_enabled}`).
- Produces: `format.activityLine(entry) -> string` (e.g. `"Model call · pai-chat · 312 tokens"`, `"Sent to openrouter · 1,204 chars"`), `format.riskLabel(kind) -> "Sends" | "Deletes" | "Spends" | "Changes system"`.

- [ ] **Step 1: Failing tests** in `format.test.js` for `activityLine` on each audit kind and `riskLabel` on each risky kind.
- [ ] **Step 2:** `npm test` → FAIL. **Step 3:** Implement components; Providers page shows the warning "Cloud models see what you send. Names and secrets are blocked or kept on this box." and never displays a stored key. **Step 4:** `npm test` → pass; `npx vite build` → success.
- [ ] **Step 5:** Browser check at `localhost:8088`: confirm a pending `delete_memory`, see it in Activity, see "Chain intact". Commit `feat: activity, approvals and providers views`.

### Task 8: End-to-end check and docs

**Files:**
- Modify: `prototype/README.md` (vault key, providers, approvals, activity, bench), `docs/COORDINATION-SUMMARY.md` (status)
- Create: `prototype/app/tests/test_e2e.py` (marked `e2e`, skipped unless `PAI_E2E=1`)

- [ ] **Step 1:** `test_e2e.py` against the running stack: interview → rules draft → chat → "remember X" → search finds X → propose delete → confirm → memory gone → `/api/activity/verify` returns intact → no `outbound` entries with cloud off.
- [ ] **Step 2:** `docker compose --profile local up -d --build && PAI_E2E=1 .venv/bin/pytest -q -m e2e` → pass.
- [ ] **Step 3:** Update README; commit `test: MVP end-to-end check; docs`.
