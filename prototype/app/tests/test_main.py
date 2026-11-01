import os
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import main
from pai import vault

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def fresh_db():
    path = os.path.join(main.DATA_DIR, "pai.db")
    if os.path.exists(path):
        os.remove(path)


def test_interview_walks_every_question_then_finishes():
    first = client.get("/api/interview").json()
    assert first == {"done": False, "key": "name", "question": main.QUESTIONS[0][1], "answered": 0, "total": 8}
    for key, _ in main.QUESTIONS:
        state = client.post("/api/interview", json={"key": key, "value": f"answer {key}"}).json()
    assert state["done"] is True and state["answered"] == 8


def test_interview_rejects_unknown_key_and_empty_answer():
    assert client.post("/api/interview", json={"key": "ssn", "value": "x"}).status_code == 400
    assert client.post("/api/interview", json={"key": "name", "value": "  "}).status_code == 400


def test_rules_draft_needs_finished_interview():
    assert client.post("/api/rules/draft").status_code == 400


def test_remember_stores_memory_without_calling_model_and_can_be_forgotten():
    r = client.post("/api/chat", json={"message": "Remember that my dentist is on Fridays"}).json()
    assert r["reply"] == "Saved to memory on this box."
    mems = client.get("/api/memories").json()
    assert [m["text"] for m in mems] == ["my dentist is on Fridays"]
    client.delete(f"/api/memories/{mems[0]['id']}")
    assert client.get("/api/memories").json() == []


def test_recall_ranks_by_shared_words_and_skips_unrelated():
    for t in ["dentist appointment on Fridays", "favorite coffee is oat latte", "dentist is Dr Lee"]:
        client.post("/api/chat", json={"message": f"remember {t}"})
    with closing(main.db()) as con:
        got = vault.search(con, "when is my dentist appointment")
    assert got[0] == "dentist appointment on Fridays"
    assert "favorite coffee is oat latte" not in got


def test_system_prompt_includes_profile_rules_and_memories():
    client.post("/api/interview", json={"key": "name", "value": "Sam"})
    client.put("/api/rules", json={"text": "I won't email anyone without asking."})
    client.post("/api/chat", json={"message": "remember the board meeting is Tuesday"})
    p = main.system_prompt("what about the board meeting")
    assert "name: Sam" in p and "I won't email anyone" in p and "board meeting is Tuesday" in p


def test_think_tags_are_stripped():
    assert main.THINK.sub("", "<think>hmm</think>Hello").strip() == "Hello"


def test_empty_chat_is_rejected():
    assert client.post("/api/chat", json={"message": " "}).status_code == 400


def test_voice_endpoints_reject_empty_audio():
    for path in ("/api/voice", "/api/transcribe"):
        assert client.post(path, files={"audio": ("a.webm", b"", "audio/webm")}).status_code == 400


def test_speak_rejects_empty_text():
    assert client.post("/api/speak", json={"text": "  "}).status_code == 400
