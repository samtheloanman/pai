"""PAI prototype app: first-boot interview, chat with local memory, voice in/out.

All model calls go through LiteLLM (OpenAI-compatible) so the same app runs on a
laptop, a cloud VM or a PAI box. State lives in one SQLite file under DATA_DIR.
"""
import asyncio
import base64
import json
import logging
import os
import re
import time
from contextlib import asynccontextmanager, closing

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pai import actions, audit, embed, masking, providers, routing, store, vault, vaultkey

LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "")
DATA_DIR = os.getenv("DATA_DIR", "/data")
CHAT_MODEL = os.getenv("CHAT_MODEL", "pai-chat")
DECIDE_MODEL = os.getenv("DECIDE_MODEL", "pai-decide")
STT_MODEL = os.getenv("STT_MODEL", "pai-stt")
TTS_MODEL = os.getenv("TTS_MODEL", "pai-tts")
TTS_VOICE = os.getenv("TTS_VOICE", "af_heart")
STATIC = os.path.join(os.path.dirname(__file__), "static")

# The first-boot interview ("grill me"). Keys are stored in the profile table.
QUESTIONS = [
    ("name", "What should I call you?"),
    ("work", "What do you do for work, in a sentence or two?"),
    ("apps", "Which apps do you live in every day? Calendar, email, notes, chat?"),
    ("help", "What do you most want help with?"),
    ("off_limits", "What should I never do or never bring up?"),
    ("tone", "How should I talk to you: short and direct, or more detail?"),
    ("schedule", "When are you usually working, and when should I stay quiet?"),
    ("people", "Who are the people you mention most, and who are they to you?"),
]

log = logging.getLogger("pai")
THINK = re.compile(r"<think>.*?</think>", re.S)


def db():
    os.makedirs(DATA_DIR, exist_ok=True)
    return store.connect(os.path.join(DATA_DIR, "pai.db"), key=vaultkey.get())


def profile() -> dict[str, str]:
    with closing(db()) as con:
        return dict(con.execute("select key, value from profile").fetchall())


def rules() -> str:
    with closing(db()) as con:
        row = con.execute("select text from rules where id = 1").fetchone()
    return row[0] if row else ""


def system_prompt(query: str) -> str:
    p = profile()
    lines = [
        "You are PAI, a private assistant that runs on the owner's own hardware.",
        "Be brief and concrete. Never claim to have sent, deleted or bought anything; say what you would do and ask first.",
    ]
    if p:
        lines.append("About the owner:\n" + "\n".join(f"- {k}: {v}" for k, v in p.items()))
    if r := rules():
        lines.append("Rules the owner approved (follow them):\n" + r)
    with closing(db()) as con:
        try:
            mem = vault.search(con, query, embed=embed.embed)
        except Exception as e:  # embedder unavailable: keyword search only
            log.warning("vector search unavailable, using keywords only: %s", e)
            mem = vault.search(con, query)
    if mem:
        lines.append("Relevant memories:\n" + "\n".join(f"- {m}" for m in mem))
    return "\n\n".join(lines)


def audited(kind: str, **fields) -> int:
    """Write the audit entry or fail the request: a box that cannot audit must not silently act."""
    try:
        return audit.record(kind, **fields)
    except Exception:
        log.exception("audit write failed (%s)", kind)
        raise HTTPException(500, "audit log unavailable") from None


def _base_v1() -> str:
    base = LITELLM_URL.rstrip("/")
    return base if base.endswith("/v1") else f"{base}/v1"


def audit_model(model: str, t0: float, ok: bool, **extra) -> None:
    audited("model_call", **{"gen_ai.request.model": model}, duration_ms=int((time.monotonic() - t0) * 1000), success=ok, **extra)


async def llm(messages: list[dict], model: str | None = None, temperature: float = 0.4) -> str:
    model = model or CHAT_MODEL
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=300) as c:
            r = await c.post(
                f"{_base_v1()}/chat/completions",
                headers={"Authorization": f"Bearer {LITELLM_KEY}"},
                json={"model": model, "messages": messages, "temperature": temperature},
            )
    except httpx.HTTPError as e:
        audit_model(model, t0, False, error=type(e).__name__)
        raise
    if r.status_code != 200:
        audit_model(model, t0, False, error=f"HTTP {r.status_code}")
        raise HTTPException(502, f"model error {r.status_code}: {r.text[:200]}")
    try:  # the request already left: a malformed 200 is audited as a failure before we raise
        body = r.json()
        out = THINK.sub("", body["choices"][0]["message"]["content"]).strip()
        usage = body.get("usage") or {}
        tokens = {f"gen_ai.usage.{k}_tokens": usage[v] for k, v in (("input", "prompt_tokens"), ("output", "completion_tokens")) if v in usage}
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as e:
        audit_model(model, t0, False, error=type(e).__name__)
        raise HTTPException(502, "model returned a malformed response") from None
    # written after the call: if this audit write fails the request returns 500 although the model call already happened
    audit_model(model, t0, True, prompt=json.dumps(messages), reply=out, **tokens)
    return out


async def decide(text: str) -> tuple[str, float]:
    """Tier-3 router: ask the decision model for {"route", "p"}. Raises on any bad answer; routing maps that to chat."""
    out = await llm([
        {"role": "system", "content": f'Classify the owner\'s request into exactly one route from {list(routing.ROUTES)}. Reply with JSON only: {{"route": "<route>", "p": <0..1>}}'},
        {"role": "user", "content": text[: routing.MAX_CHARS]},
    ], model=DECIDE_MODEL, temperature=0)
    d = json.loads(out)
    if d["route"] not in routing.ROUTES:
        raise ValueError(f"unknown route {d['route']!r}")
    return d["route"], min(1.0, max(0.0, float(d["p"])))


SPEACHES_URL = os.getenv("SPEACHES_URL", "")
VOICE_MODELS = ["Systran/faster-whisper-small", "speaches-ai/Kokoro-82M-v1.0-ONNX"]


async def fetch_voice_models() -> None:
    """Ask the local voice server to download its models once; failures only log, chat still works."""
    if not SPEACHES_URL:
        return
    async with httpx.AsyncClient(timeout=900) as c:
        for m in VOICE_MODELS:
            for attempt in range(1, 7):  # the voice server may still be starting
                try:
                    r = await c.post(f"{SPEACHES_URL}/v1/models/{m}")
                    if r.status_code < 300:
                        break
                    print(f"voice model {m}: HTTP {r.status_code} (attempt {attempt})")
                except httpx.HTTPError as e:
                    print(f"voice model {m} not fetched yet (attempt {attempt}): {e}")
                await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(_: FastAPI):
    asyncio.create_task(fetch_voice_models())
    yield


def check_vault() -> None:
    """Refuse to start (no silent unencrypted mode) if the vault key is missing or wrong."""
    try:
        vaultkey.get()
    except vaultkey.NoVaultKey as e:
        raise SystemExit(str(e)) from e
    try:
        db().close()
    except vault.VaultKeyError as e:
        raise SystemExit(f"Cannot open vault: {e}") from e


check_vault()
if audit.verify() is None:
    audit.checkpoint()  # protects the log up to this boot
app = FastAPI(title="PAI prototype", lifespan=lifespan)


class Answer(BaseModel):
    key: str
    value: str


class Chat(BaseModel):
    message: str
    history: list[dict] = []
    cloud: bool = False  # the owner's per-request choice; routing never picks cloud on its own


class RulesIn(BaseModel):
    text: str


@app.get("/api/interview")
def interview():
    p = profile()
    nxt = next(((k, q) for k, q in QUESTIONS if k not in p), None)
    return {"done": nxt is None, "key": nxt and nxt[0], "question": nxt and nxt[1], "answered": len(p), "total": len(QUESTIONS)}


@app.get("/api/onboarding")
def get_onboarding():
    p = profile()
    r = rules()
    nxt = next(((k, q) for k, q in QUESTIONS if k not in p), None)
    return {
        "done": nxt is None and bool(r.strip()),
        "interview_done": nxt is None,
        "rules_ready": bool(r.strip()),
        "answered": len(p),
        "total": len(QUESTIONS),
        "next_key": nxt and nxt[0],
        "next_question": nxt and nxt[1],
        "answers": p,
        "questions": [{"key": k, "question": q, "answer": p.get(k, "")} for k, q in QUESTIONS],
        "rules": r,
        "local_stack": {
            "llm": CHAT_MODEL,
            "decide": DECIDE_MODEL,
            "stt": STT_MODEL,
            "tts": TTS_MODEL,
            "voice": TTS_VOICE,
            "cloud_enabled": providers.cloud_enabled(),
        },
    }


@app.post("/api/onboarding/reset")
def reset_onboarding():
    audited("config_changed", what="onboarding_reset")
    with closing(db()) as con, con:
        con.execute("delete from profile")
        con.execute("delete from rules")
    return get_onboarding()


@app.post("/api/onboarding/compile")
def compile_onboarding():
    p = profile()
    if len(p) < len(QUESTIONS):
        raise HTTPException(400, "finish the interview first")
    r = rules()
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with closing(db()) as con, con:
        # 1. Update onboarding_profile
        for k, v in p.items():
            cat = "identity" if k in ("name", "work", "people") else \
                  "boundary" if k in ("off_limits", "schedule") else \
                  "stack" if k in ("apps", "tone") else "optimization"
            chash = f"{k}:{v}"
            con.execute(
                "insert into onboarding_profile (key, value, category, compiled_hash, updated_at) "
                "values (?, ?, ?, ?, ?) on conflict(key) do update set "
                "value = excluded.value, category = excluded.category, "
                "compiled_hash = excluded.compiled_hash, updated_at = excluded.updated_at",
                (k, v, cat, chash, now_iso)
            )

        # 2. Compile agent_personas
        name = p.get("name", "Owner")
        work = p.get("work", "")
        tone = p.get("tone", "short and direct")
        help_need = p.get("help", "")
        off_limits = p.get("off_limits", "")
        sched = p.get("schedule", "")
        system_prompt = (
            f"You are PAI, a sovereign private AI assistant for {name}.\n"
            f"Owner Profile:\n- Work: {work}\n- Tone: {tone}\n- Goals: {help_need}\n- Off-limits: {off_limits}\n"
            f"Schedule: {sched}\n"
            f"Constitutional Rules:\n{r.strip() if r.strip() else 'Never leak data outside local device.'}"
        )
        con.execute(
            "insert into agent_personas (persona_id, display_name, system_prompt, loop_mode, preferred_model, quiet_hours_json, active) "
            "values (?, ?, ?, ?, ?, ?, 1) on conflict(persona_id) do update set "
            "display_name = excluded.display_name, system_prompt = excluded.system_prompt, "
            "preferred_model = excluded.preferred_model",
            ("pai-default", "PAI Sovereign Companion", system_prompt, "react", CHAT_MODEL, '{"start":"22:00","end":"07:00"}')
        )

        # 3. Populate skills_and_tools
        apps_lower = p.get("apps", "").lower()
        tools = [
            ("memory-vault", "Encrypted Memory Vault", "box_sandbox", "{}", "none", 0, 1),
            ("calendar-sync", "Calendar Synchronizer", "box_sandbox", "{}", "none", 0, 1 if "cal" in apps_lower else 0),
            ("himalaya-email", "Local Email Client", "box_sandbox", "{}", "send", 0, 1 if "mail" in apps_lower or "email" in apps_lower else 0),
            ("notes-manager", "Markdown Notes Manager", "box_sandbox", "{}", "none", 0, 1 if "note" in apps_lower else 0),
            ("system-terminal", "Isolated Bash Runner", "box_sandbox", "{}", "system", 0, 0),
        ]
        enabled_skills = []
        for sid, title, plane, schema_md, risk, score, en in tools:
            con.execute(
                "insert into skills_and_tools (skill_id, title, execution_plane, schema_or_md, risk_kind, skillspector_score, enabled_by_onboarding) "
                "values (?, ?, ?, ?, ?, ?, ?) on conflict(skill_id) do update set "
                "title = excluded.title, enabled_by_onboarding = excluded.enabled_by_onboarding",
                (sid, title, plane, schema_md, risk, score, en)
            )
            if en == 1:
                enabled_skills.append(sid)

        # 4. Populate connections_ingress
        con.execute(
            "insert into connections_ingress (conn_id, conn_type, door_plane, privacy_tier, endpoint_or_model, secret_key, enabled, updated_at) "
            "values (?, ?, ?, ?, ?, ?, ?, ?) on conflict(conn_id) do update set "
            "enabled = excluded.enabled, updated_at = excluded.updated_at",
            ("pai-mobile-app", "comm_channel", "door1_mesh", "A", "127.0.0.1", None, 1, time.time())
        )
        con.execute(
            "insert into connections_ingress (conn_id, conn_type, door_plane, privacy_tier, endpoint_or_model, secret_key, enabled, updated_at) "
            "values (?, ?, ?, ?, ?, ?, ?, ?) on conflict(conn_id) do update set "
            "enabled = excluded.enabled, updated_at = excluded.updated_at",
            ("ollama", "model_provider", "door1_mesh", "A", LITELLM_URL, None, 1, time.time())
        )

    audited("config_changed", what="onboarding_compile")
    return {
        "ok": True,
        "compiled_at": now_iso,
        "persona_id": "pai-default",
        "system_prompt": system_prompt,
        "skills_enabled": enabled_skills,
        "onboarding_profile_count": len(p),
    }



@app.post("/api/interview")
def answer(a: Answer):
    if a.key not in dict(QUESTIONS):
        raise HTTPException(400, "unknown question")
    if not a.value.strip():
        raise HTTPException(400, "answer is empty")
    audited("config_changed", what="interview", key=a.key)
    with closing(db()) as con, con:
        con.execute("insert into profile (key, value) values (?, ?) on conflict(key) do update set value = excluded.value", (a.key, a.value.strip()))
    return interview()


@app.post("/api/rules/draft")
async def draft_rules():
    p = profile()
    if len(p) < len(QUESTIONS):
        raise HTTPException(400, "finish the interview first")
    text = await llm([
        {"role": "system", "content": "You are PAI, the owner's assistant. Write a short plain-English page with two headed lists, 'I will' and 'I won't', where 'I' is PAI describing how it will help the owner. Base it only on the interview. No preamble."},
        {"role": "user", "content": "\n".join(f"{k}: {v}" for k, v in p.items())},
    ])
    audited("config_changed", what="rules", via="draft")
    with closing(db()) as con, con:
        con.execute("insert into rules (id, text) values (1, ?) on conflict(id) do update set text = excluded.text", (text,))
    return {"text": text}


@app.get("/api/rules")
def get_rules():
    return {"text": rules()}


@app.put("/api/rules")
def put_rules(r: RulesIn):
    audited("config_changed", what="rules", via="edit")
    with closing(db()) as con, con:
        con.execute("insert into rules (id, text) values (1, ?) on conflict(id) do update set text = excluded.text", (r.text,))
    return {"text": r.text}


@app.get("/api/memories")
def memories():
    with closing(db()) as con:
        return [{"id": i, "text": t, "created": c} for i, t, c in con.execute("select id, text, created from memories order by id desc")]


@app.delete("/api/memories/{mid}")
def forget(mid: int):
    # accepted: memory_deleted is written before the delete, so it can record a delete that then fails or targets a missing id
    audited("memory_deleted", memory_id=mid)
    with closing(db()) as con, con:
        con.execute("delete from memories where id = ?", (mid,))
    return {"ok": True}


def add_memory(text: str) -> int:
    with closing(db()) as con:
        try:
            return vault.add_memory(con, text, embed=embed.embed)
        except Exception as e:  # embedder unavailable: store for keyword search only
            log.warning("memory saved without vector: %s", e)
            return vault.add_memory(con, text)


async def reply_to(message: str, history: list[dict], want_cloud: bool = False) -> str:
    message = message[: routing.MAX_CHARS]
    r = await routing.route(message, embed=embed.embed, decide=decide)
    audited("route", **{"pai.route": r.name}, tier=r.tier, score=r.score)
    # only the rule tier may write memory or prompt for approval; a model verdict never does
    if r.name == "remember" and r.tier == 1:
        m = re.match(r"^\s*remember(?: that)?[:,]?\s+(.+)", message, re.I | re.S)
        text = m.group(1).strip()
        mid = add_memory(text)  # id is only known after the insert, so undo it if the audit write fails
        try:
            audited("memory_added", memory_id=mid, text=text)
        except HTTPException:
            with closing(db()) as con, con:
                con.execute("delete from memories where id = ?", (mid,))
            raise
        return "Saved to memory on this box."
    if r.name == "action" and r.tier == 1:
        mid = int(re.match(r"^\s*(?:forget|delete)\s+memory\s+(\d+)", message, re.I).group(1))
        with closing(db()) as con:
            row = con.execute("select text from memories where id = ?", (mid,)).fetchone()
        if not row:
            return f"I can't find memory {mid}."
        snippet = row[0][:80]
        try:  # proposing never deletes: the owner approves on the Approvals page
            actions.propose("delete", f'Delete memory {mid}: "{snippet}"', {"executor": "delete_memory", "memory_id": mid})
        except actions.AuditUnavailable:
            raise HTTPException(500, "audit log unavailable") from None
        return f'I can delete memory {mid} ("{snippet}"). Approve it on the Approvals page.'
    hist = history[-10:]
    model, why = providers.cloud_decision("\n".join([message, *(str(h.get("content", "")) for h in hist)]), want_cloud)
    if model == "pai-cloud":
        # minimal fixed prompt: never the owner's profile, rules or memories
        mk = masking.Masker([profile().get("name", "")])
        msgs = [{"role": "system", "content": providers.CLOUD_SYSTEM},
                *({"role": "assistant" if h.get("role") == "assistant" else "user", "content": mk.mask(str(h.get("content", "")))} for h in hist),
                {"role": "user", "content": mk.mask(message)}]
        audited("outbound", **{"pai.provider": providers.cloud_provider(), "chars": sum(len(m["content"]) for m in msgs), "pai.masked_fields": mk.count})
        return mk.unmask(await llm(msgs, model=model))
    msgs = [{"role": "system", "content": system_prompt(message)}, *hist, {"role": "user", "content": message}]
    out = await llm(msgs)
    return f"I kept that on this box: {why}.\n\n{out}" if want_cloud else out


@app.post("/api/route")
async def route_only(c: Chat):
    """Debug/bench: classify a message without executing anything."""
    r = await routing.route(c.message, embed=embed.embed, decide=decide)
    return {"route": r.name, "tier": r.tier, "score": r.score}


@app.post("/api/chat")
async def chat(c: Chat):
    if not c.message.strip():
        raise HTTPException(400, "message is empty")
    return {"reply": await reply_to(c.message, c.history, c.cloud)}


async def transcribe_bytes(c: httpx.AsyncClient, data: bytes, name: str, ctype: str) -> str:
    t0 = time.monotonic()
    try:
        t = await c.post(
            f"{_base_v1()}/audio/transcriptions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            data={"model": STT_MODEL},
            files={"file": (name, data, ctype)},
        )
    except httpx.HTTPError as e:
        audit_model(STT_MODEL, t0, False, error=type(e).__name__)
        raise HTTPException(502, "speech-to-text unreachable") from None
    audit_model(STT_MODEL, t0, t.status_code == 200, **({} if t.status_code == 200 else {"error": f"HTTP {t.status_code}"}))
    if t.status_code != 200:
        raise HTTPException(502, f"speech-to-text error {t.status_code}: {t.text[:200]}")
    return t.json().get("text", "").strip()


async def synthesize(c: httpx.AsyncClient, text: str):
    t0 = time.monotonic()
    try:
        s = await c.post(
            f"{LITELLM_URL}/v1/audio/speech",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": TTS_MODEL, "input": text[:1500], "voice": TTS_VOICE, "response_format": "mp3"},
        )
    except httpx.HTTPError as e:
        audit_model(TTS_MODEL, t0, False, error=type(e).__name__)
        raise HTTPException(502, "text-to-speech unreachable") from None
    audit_model(TTS_MODEL, t0, s.status_code == 200, **({} if s.status_code == 200 else {"error": f"HTTP {s.status_code}"}))
    return s


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile):
    """Speech to text only; the setup interview fills the answer box and saves nothing until Next."""
    data = await audio.read()
    if not data:
        raise HTTPException(400, "no audio")
    async with httpx.AsyncClient(timeout=300) as c:
        return {"text": await transcribe_bytes(c, data, audio.filename or "speech.webm", audio.content_type or "audio/webm")}


class Speak(BaseModel):
    text: str


@app.post("/api/speak")
async def speak(body: Speak):
    """Text to speech on the box; returns base64 mp3 for the chat's read-aloud toggle."""
    if not body.text.strip():
        raise HTTPException(400, "text is empty")
    async with httpx.AsyncClient(timeout=300) as c:
        s = await synthesize(c, body.text)
    if s.status_code != 200:
        raise HTTPException(502, f"text-to-speech error {s.status_code}")
    return {"audio": base64.b64encode(s.content).decode()}


@app.post("/api/voice")
async def voice(audio: UploadFile):
    """Speech in, speech out: transcribe, answer, speak. All three calls stay on the box via LiteLLM."""
    data = await audio.read()
    if not data:
        raise HTTPException(400, "no audio")
    async with httpx.AsyncClient(timeout=300) as c:
        heard = await transcribe_bytes(c, data, audio.filename or "speech.webm", audio.content_type or "audio/webm")
        reply = await reply_to(heard, []) if heard else "I didn't catch that."
        s = await synthesize(c, reply)
    audio_b64 = base64.b64encode(s.content).decode() if s.status_code == 200 else None
    return {"heard": heard, "reply": reply, "audio": audio_b64}


@app.get("/api/actions")
def list_actions():
    return actions.pending()


@app.post("/api/actions/{aid}/confirm")
def confirm_action(aid: str):
    try:
        return actions.confirm(aid)
    except actions.AuditUnavailable:
        raise HTTPException(500, "audit log unavailable") from None


@app.post("/api/actions/{aid}/reject")
def reject_action(aid: str):
    try:
        actions.reject(aid)
    except actions.AuditUnavailable:
        raise HTTPException(500, "audit log unavailable") from None
    return {"ok": True}


@app.get("/api/activity")
def activity(kind: str | None = None, limit: int = 100):
    return audit.entries(limit=limit, kind=kind)


@app.get("/api/activity/verify")
def activity_verify():
    bad = audit.verify()
    if bad is None:
        audit.checkpoint()  # only a clean log is checkpointed; protects it up to now
    return {"intact": bad is None, "first_broken": bad}


class ProviderIn(BaseModel):
    name: str
    key: str | None = None
    model: str | None = None
    base: str | None = None  # local backends only (ollama, lmstudio)


class CloudIn(BaseModel):
    enabled: bool


def providers_state() -> dict:
    r = providers.rows()
    return {"cloud_enabled": providers.cloud_enabled(), "warning": providers.WARNING,
            "restart_required": providers.get_setting("restart_pending") == "1",
            "providers": [{"name": n, "has_key": bool(r.get(n, {}).get("key")), "model": r.get(n, {}).get("model"),
                           "cloud": n in providers.CLOUD} for n in providers.PROVIDERS]}


def provider_change(action: str, apply, provider: str | None = None) -> None:
    """Audit first (fail closed), then apply. Entries carry the provider name only: no key or model text."""
    audited("config_changed", what="providers", action=action, **({"provider": provider} if provider else {}))
    apply()
    providers.set_setting("restart_pending", "1")
    providers.write_files()


@app.get("/api/providers")
def get_providers():
    return providers_state()


@app.put("/api/providers")
def put_provider(p: ProviderIn):
    if p.name not in providers.PROVIDERS:
        raise HTTPException(400, "unknown provider")
    key = p.key.strip() if p.key is not None else None
    if key and not providers.KEY_RE.fullmatch(key):
        raise HTTPException(400, "key must be 1-512 printable ASCII characters with no spaces")
    if p.model and not p.model.strip().startswith(providers.PROVIDERS[p.name]):
        raise HTTPException(400, f"model must start with {providers.PROVIDERS[p.name]}")
    if key and p.name in providers.LOCAL_BACKENDS:
        raise HTTPException(400, "this provider runs on a local server and takes no key")
    if key is not None:
        provider_change("key_set" if key else "key_removed", lambda: providers.save_key(p.name, key), p.name)
    if p.model is not None:
        provider_change("model_set", lambda: providers.save_model(p.name, p.model.strip()), p.name)
    if p.base is not None and p.name in providers.LOCAL_BACKENDS:
        provider_change("base_set", lambda: providers.set_setting(f"{p.name}_base", p.base.strip()), p.name)
    return {**providers_state(), "restart_required": True}


@app.post("/api/providers/restarted")
def providers_restarted():
    """The owner confirms they restarted litellm; clears restart_required."""
    audited("config_changed", what="providers", action="restart_ack")
    providers.set_setting("restart_pending", "0")
    return providers_state()


@app.put("/api/providers/cloud")
def put_cloud(c: CloudIn):
    provider_change("cloud_on" if c.enabled else "cloud_off", lambda: providers.set_cloud_enabled(c.enabled))
    return {**providers_state(), "restart_required": True}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
