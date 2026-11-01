"""End-to-end check against a live server + fake LiteLLM. Run with ./run-e2e.sh (sets PAI_E2E=1)."""
import os

import httpx
import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.skipif(os.getenv("PAI_E2E") != "1", reason="set PAI_E2E=1 (see run-e2e.sh)")]

BASE = os.getenv("PAI_E2E_BASE", "http://127.0.0.1:8099")
FAKE = os.getenv("PAI_E2E_FAKE", "http://127.0.0.1:4999")
ANSWERS = {"name": "Zorblax", "work": "Quillwright of lanterns", "apps": "Frobnicator and Glimmer",
           "help": "Sorting my wibble schedule", "off_limits": "Never mention the plinth",
           "tone": "short and direct", "schedule": "Nine to five on Tuesdays", "people": "Gwendolyn is my cousin"}
CARD = "4111 1111 1111 1111 12/27"


def fake_requests():
    return httpx.get(f"{FAKE}/requests").json()["requests"]


def cloud_requests():
    return [r for r in fake_requests() if r.get("model") == "pai-cloud"]


def test_full_flow():
    c = httpx.Client(base_url=BASE, timeout=60)

    def chat(message, **kw):
        r = c.post("/api/chat", json={"message": message, **kw})
        assert r.status_code == 200, r.text
        return r.json()["reply"]

    # 1 interview
    for k, v in ANSWERS.items():
        assert c.post("/api/interview", json={"key": k, "value": v}).status_code == 200
    assert c.get("/api/interview").json()["done"] is True
    # 2 rules
    assert c.post("/api/rules/draft").json()["text"] == "fake model reply"
    # 3 chat
    assert chat("hello there") == "fake model reply"
    # 4 remember
    assert chat("remember my cat is called Miso") == "Saved to memory on this box."
    # 5 memory search reaches the prompt
    mems = c.get("/api/memories").json()
    mem = next(m for m in mems if "Miso" in m["text"])
    n = len(fake_requests())
    chat("what is my cat called Miso?")
    sent = fake_requests()[n:]
    assert any("Miso" in str(r["messages"][0]["content"]) for r in sent if r["messages"][0]["role"] == "system")
    # 6 delete is only proposed
    assert "Approvals" in chat(f"delete memory {mem['id']}")
    assert any(m["id"] == mem["id"] for m in c.get("/api/memories").json())
    # 7 exactly one pending action, no payload
    acts = c.get("/api/actions").json()
    assert len(acts) == 1 and "payload" not in acts[0]
    # 8 confirm -> done, memory gone; 9 second confirm -> already_done
    assert c.post(f"/api/actions/{acts[0]['id']}/confirm").json()["status"] == "done"
    assert not any(m["id"] == mem["id"] for m in c.get("/api/memories").json())
    assert c.post(f"/api/actions/{acts[0]['id']}/confirm").json()["status"] == "already_done"
    # 10 audit
    assert c.get("/api/activity/verify").json()["intact"] is True
    log = c.get("/api/activity?limit=500").json()
    kinds = {e["kind"] for e in log}
    assert {"model_call", "route", "action_proposed", "action_confirmed", "memory_added", "memory_deleted"} <= kinds
    blob = str(log)
    assert "Miso" not in blob and not any(v in blob for v in ANSWERS.values())
    # 11 cloud off: per-request flag alone never reaches pai-cloud
    chat("hello", cloud=True)
    assert cloud_requests() == [] and not [e for e in c.get("/api/activity?kind=outbound").json()]
    # 12 cloud on: blocked content stays local, harmless content goes out minimally
    assert c.put("/api/providers", json={"name": "openrouter", "key": "test-key-123"}).status_code == 200
    assert c.put("/api/providers/cloud", json={"enabled": True}).status_code == 200
    assert chat(f"please check {CARD}", cloud=True).startswith("I kept that on this box:")
    assert cloud_requests() == []
    chat("what is the capital of France", cloud=True)
    sent = cloud_requests()
    assert len(sent) == 1
    payload = str(sent[0])
    assert not any(v in payload for v in ANSWERS.values()) and "Miso" not in payload and "fake model reply" not in payload
    out = c.get("/api/activity?kind=outbound").json()
    assert len(out) == 1 and set(out[0]["fields"]) <= {"pai.provider", "chars", "pai.masked_fields"}
    assert out[0]["fields"]["pai.provider"] == "openrouter"
    # 13 the key is never returned
    assert "test-key-123" not in c.get("/api/providers").text
