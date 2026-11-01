"""PAI prototype app: first-boot interview, chat with local memory, voice in/out.

All model calls go through LiteLLM (OpenAI-compatible) so the same app runs on a
laptop, a cloud VM or a PAI box. State lives in one SQLite file under DATA_DIR.
"""
import asyncio
import base64
import os
import re
import sqlite3
from contextlib import asynccontextmanager, closing

import httpx
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pai import store

LITELLM_URL = os.getenv("LITELLM_URL", "http://litellm:4000")
LITELLM_KEY = os.getenv("LITELLM_MASTER_KEY", "")
DATA_DIR = os.getenv("DATA_DIR", "/data")
CHAT_MODEL = os.getenv("CHAT_MODEL", "pai-chat")
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

THINK = re.compile(r"<think>.*?</think>", re.S)


def db() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    return store.connect(os.path.join(DATA_DIR, "pai.db"))


def profile() -> dict[str, str]:
    with closing(db()) as con:
        return dict(con.execute("select key, value from profile").fetchall())


def rules() -> str:
    with closing(db()) as con:
        row = con.execute("select text from rules where id = 1").fetchone()
    return row[0] if row else ""


def recall(query: str, limit: int = 5) -> list[str]:
    """Memories sharing the most words (4+ letters) with the query. shortcut: keyword overlap, swap for sqlite-vec embeddings when memories exceed a few hundred."""
    words = {w for w in re.findall(r"[a-z0-9]{4,}", query.lower())}
    with closing(db()) as con:
        rows = [r[0] for r in con.execute("select text from memories order by id desc").fetchall()]
    scored = sorted(((len(words & set(re.findall(r"[a-z0-9]{4,}", m.lower()))), m) for m in rows), key=lambda x: -x[0])
    return [m for s, m in scored[:limit] if s > 0]


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
    if mem := recall(query):
        lines.append("Relevant memories:\n" + "\n".join(f"- {m}" for m in mem))
    return "\n\n".join(lines)


async def llm(messages: list[dict]) -> str:
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.post(
            f"{LITELLM_URL}/v1/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": CHAT_MODEL, "messages": messages, "temperature": 0.4},
        )
    if r.status_code != 200:
        raise HTTPException(502, f"model error {r.status_code}: {r.text[:200]}")
    return THINK.sub("", r.json()["choices"][0]["message"]["content"]).strip()


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


app = FastAPI(title="PAI prototype", lifespan=lifespan)


class Answer(BaseModel):
    key: str
    value: str


class Chat(BaseModel):
    message: str
    history: list[dict] = []


class RulesIn(BaseModel):
    text: str


@app.get("/api/interview")
def interview():
    p = profile()
    nxt = next(((k, q) for k, q in QUESTIONS if k not in p), None)
    return {"done": nxt is None, "key": nxt and nxt[0], "question": nxt and nxt[1], "answered": len(p), "total": len(QUESTIONS)}


@app.post("/api/interview")
def answer(a: Answer):
    if a.key not in dict(QUESTIONS):
        raise HTTPException(400, "unknown question")
    if not a.value.strip():
        raise HTTPException(400, "answer is empty")
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
    with closing(db()) as con, con:
        con.execute("insert into rules (id, text) values (1, ?) on conflict(id) do update set text = excluded.text", (text,))
    return {"text": text}


@app.get("/api/rules")
def get_rules():
    return {"text": rules()}


@app.put("/api/rules")
def put_rules(r: RulesIn):
    with closing(db()) as con, con:
        con.execute("insert into rules (id, text) values (1, ?) on conflict(id) do update set text = excluded.text", (r.text,))
    return {"text": r.text}


@app.get("/api/memories")
def memories():
    with closing(db()) as con:
        return [{"id": i, "text": t, "created": c} for i, t, c in con.execute("select id, text, created from memories order by id desc")]


@app.delete("/api/memories/{mid}")
def forget(mid: int):
    with closing(db()) as con, con:
        con.execute("delete from memories where id = ?", (mid,))
    return {"ok": True}


async def reply_to(message: str, history: list[dict]) -> str:
    m = re.match(r"^\s*remember(?: that)?[:,]?\s+(.+)", message, re.I | re.S)
    if m:
        with closing(db()) as con, con:
            con.execute("insert into memories (text) values (?)", (m.group(1).strip(),))
        return "Saved to memory on this box."
    msgs = [{"role": "system", "content": system_prompt(message)}, *history[-10:], {"role": "user", "content": message}]
    return await llm(msgs)


@app.post("/api/chat")
async def chat(c: Chat):
    if not c.message.strip():
        raise HTTPException(400, "message is empty")
    return {"reply": await reply_to(c.message, c.history)}


async def transcribe_bytes(c: httpx.AsyncClient, data: bytes, name: str, ctype: str) -> str:
    t = await c.post(
        f"{LITELLM_URL}/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {LITELLM_KEY}"},
        data={"model": STT_MODEL},
        files={"file": (name, data, ctype)},
    )
    if t.status_code != 200:
        raise HTTPException(502, f"speech-to-text error {t.status_code}: {t.text[:200]}")
    return t.json().get("text", "").strip()


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
        s = await c.post(
            f"{LITELLM_URL}/v1/audio/speech",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={"model": TTS_MODEL, "input": body.text[:1500], "voice": TTS_VOICE, "response_format": "mp3"},
        )
    if s.status_code != 200:
        raise HTTPException(502, f"text-to-speech error {s.status_code}")
    return {"audio": base64.b64encode(s.content).decode()}


@app.post("/api/voice")
async def voice(audio: UploadFile):
    """Speech in, speech out: transcribe, answer, speak. All three calls stay on the box via LiteLLM."""
    data = await audio.read()
    if not data:
        raise HTTPException(400, "no audio")
    headers = {"Authorization": f"Bearer {LITELLM_KEY}"}
    async with httpx.AsyncClient(timeout=300) as c:
        heard = await transcribe_bytes(c, data, audio.filename or "speech.webm", audio.content_type or "audio/webm")
        reply = await reply_to(heard, []) if heard else "I didn't catch that."
        s = await c.post(
            f"{LITELLM_URL}/v1/audio/speech",
            headers=headers,
            json={"model": TTS_MODEL, "input": reply[:1500], "voice": TTS_VOICE, "response_format": "mp3"},
        )
    audio_b64 = base64.b64encode(s.content).decode() if s.status_code == 200 else None
    return {"heard": heard, "reply": reply, "audio": audio_b64}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
