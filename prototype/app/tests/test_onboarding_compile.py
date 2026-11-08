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
