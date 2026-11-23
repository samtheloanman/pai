import os
import pytest
from fastapi.testclient import TestClient
import main
from main import app, QUESTIONS

client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "DATA_DIR", str(tmp_path))


def test_compile_fails_if_interview_incomplete():
    res = client.post("/api/onboarding/compile")
    assert res.status_code == 400
    assert "finish the interview first" in res.json()["detail"]


def test_compile_succeeds_after_all_questions_answered():
    # Answer all 8 questions
    for key, _ in QUESTIONS:
        res = client.post("/api/interview", json={"key": key, "value": f"Test answer for {key}"})
        assert res.status_code == 200

    # Compile onboarding
    res = client.post("/api/onboarding/compile")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["persona_id"] == "pai-default"
    assert data["onboarding_profile_count"] == 8
    assert "Test answer for name" in data["system_prompt"]
    assert "memory-vault" in data["skills_enabled"]

    # Verify database persistence
    res_onboarding = client.get("/api/onboarding")
    assert res_onboarding.status_code == 200


def test_compile_feeds_persona_and_skills_into_system_prompt():
    assert "Compiled persona" not in main.system_prompt("hello")  # nothing compiled yet
    for key, _ in QUESTIONS:
        client.post("/api/interview", json={"key": key, "value": "zq-" + key + (" mail notes" if key == "apps" else "")})
    assert client.post("/api/onboarding/compile").status_code == 200
    sp = main.system_prompt("hello")
    assert "Compiled persona (from onboarding):" in sp
    assert "sovereign private AI assistant for zq-name" in sp and "Off-limits: zq-off_limits" in sp
    assert "Enabled local skills:" in sp and "- Encrypted Memory Vault" in sp and "- Local Email Client" in sp
    assert "Isolated Bash Runner" not in sp  # not enabled by onboarding


def test_compiled_persona_in_system_prompt_is_bounded(monkeypatch):
    from contextlib import closing
    main.db().close()  # runs migrations
    with closing(main.db()) as con, con:
        con.execute("insert into agent_personas (persona_id, display_name, system_prompt) values ('pai-default', 'x', ?)",
                    ("p" * (main.PERSONA_MAX_CHARS * 3),))
    assert main.compiled_persona()[0] == "p" * main.PERSONA_MAX_CHARS
