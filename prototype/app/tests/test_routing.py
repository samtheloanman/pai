import asyncio
import os
from contextlib import closing

import pytest
from fastapi.testclient import TestClient

import main
from pai import routing, vault

client = TestClient(main.app)


def run(coro):
    return asyncio.run(coro)


def unit(i):
    v = [0.0] * 384
    v[i] = 1.0
    return v


def make_embed(example_axis: dict):
    """Fake embedder: each route's examples map to one axis; the query 'CAL' hits calendar's axis."""
    def embed(s):
        for route, axis in example_axis.items():
            if s in routing.EXAMPLES.get(route, []) or s == f"QUERY_{route}":
                return unit(axis)
        return [0.0] * 384
    return embed


EMB = make_embed({"memory_query": 0, "calendar": 1, "email": 2})


async def fake_decide(t):
    return "chat", 0.5


def test_rule_tier_catches_remember():
    r = run(routing.route("Remember that rent is due on the 1st"))
    assert (r.name, r.tier) == ("remember", 1)


def test_rule_tier_forget_memory_is_action():
    r = run(routing.route("forget memory 3"))
    assert (r.name, r.tier) == ("action", 1)
    assert run(routing.route("  Delete memory 12 please")).name == "action"


def test_embedding_tier_used_when_confident():
    r = run(routing.route("QUERY_calendar", embed=EMB))
    assert (r.name, r.tier) == ("calendar", 2)


def test_model_tier_only_when_embedding_unsure():
    calls = []

    async def decide(t):
        calls.append(t)
        return "chat", 0.8

    r = run(routing.route("hmm", embed=lambda s: [0.0] * 384, decide=decide))
    assert r.tier == 3 and len(calls) == 1


def test_long_input_is_truncated():
    seen = []
    run(routing.route("x" * 50_000, embed=lambda s: seen.append(len(s)) or [0.0] * 384, decide=fake_decide))
    assert max(seen) <= routing.MAX_CHARS


def test_long_input_is_truncated_for_decide():
    seen = []

    async def decide(t):
        seen.append(len(t))
        return "chat", 0.5

    run(routing.route("x" * 50_000, embed=lambda s: [0.0] * 384, decide=decide))
    assert seen and max(seen) <= routing.MAX_CHARS


def test_embedder_failure_skips_tier_2():
    def boom(s):
        raise RuntimeError("download failed")

    r = run(routing.route("what is on my calendar", embed=boom, decide=fake_decide))
    assert r.tier == 3
    r = run(routing.route("what is on my calendar", embed=boom))
    assert (r.name, r.tier) == ("chat", 3)


def test_decide_without_model_falls_back_to_chat():
    r = run(routing.route("hmm", embed=lambda s: [0.0] * 384))
    assert r.name == "chat"


def _decide_with(monkeypatch, handler):
    import httpx
    real = httpx.AsyncClient

    def client_factory(*a, **k):
        return real(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(main.httpx, "AsyncClient", client_factory)


def _reply(content):
    import httpx
    return lambda req: httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_model_decide_valid_json(monkeypatch):
    _decide_with(monkeypatch, _reply('{"route": "email", "p": 0.9}'))
    assert run(main.decide("check my inbox")) == ("email", 0.9)


@pytest.mark.parametrize("content", ["not json at all", '{"route": "launch_missiles", "p": 1}', '{"route": "email"}'])
def test_model_decide_bad_output_is_chat(monkeypatch, content):
    _decide_with(monkeypatch, _reply(content))
    r = run(routing.route("hmm", embed=lambda s: [0.0] * 384, decide=main.decide))
    assert (r.name, r.tier, r.score) == ("chat", 3, 0.0)


def test_model_decide_http_error_is_chat(monkeypatch):
    import httpx
    _decide_with(monkeypatch, lambda req: httpx.Response(500, text="boom"))
    r = run(routing.route("hmm", embed=lambda s: [0.0] * 384, decide=main.decide))
    assert (r.name, r.tier, r.score) == ("chat", 3, 0.0)


def test_examples_embedded_once():
    routing._example_vecs = None
    n = []
    def counting(s):
        n.append(s)
        return [0.0] * 384
    run(routing.route("a", embed=counting, decide=fake_decide))
    first = len(n)
    run(routing.route("b", embed=counting, decide=fake_decide))
    assert len(n) == first + 1


def test_forget_message_deletes_nothing():
    path = os.path.join(main.DATA_DIR, "pai.db")
    if os.path.exists(path):
        os.remove(path)
    with closing(main.db()) as con:
        mid = vault.add_memory(con, "keep me")
    r = client.post("/api/chat", json={"message": f"forget memory {mid}"}).json()
    assert "Approvals page" in r["reply"] and f"memory {mid}" in r["reply"]
    assert [m["text"] for m in client.get("/api/memories").json()] == ["keep me"]


def test_route_endpoint_is_inert():
    before = _count()
    r = client.post("/api/route", json={"message": "Remember that x"}).json()
    assert r["route"] == "remember" and r["tier"] == 1 and "score" in r
    assert _count() == before


def test_failing_embedder_does_not_break_chat_memory(monkeypatch):
    from pai import embed

    def boom(s):
        raise RuntimeError("no model")
    monkeypatch.setattr(embed, "embed", boom)
    assert client.post("/api/chat", json={"message": "remember that tea is good"}).json()["reply"] == "Saved to memory on this box."


def _count():
    return len(client.get("/api/memories").json())


def test_model_cannot_trigger_remember_or_action(monkeypatch):
    async def fake_llm(messages, model=None):
        return "chat reply"
    monkeypatch.setattr(main, "llm", fake_llm)
    for verdict in ("remember", "action"):
        async def dec(t, v=verdict):
            return v, 0.9
        monkeypatch.setattr(main, "decide", dec)
        before = _count()
        r = client.post("/api/chat", json={"message": "zzqx what is the capital of France"})
        assert r.status_code == 200 and r.json()["reply"] == "chat reply"
        assert _count() == before


def test_long_chat_message_truncated_before_embedder(monkeypatch):
    from pai import embed
    seen = []
    monkeypatch.setattr(embed, "embed", lambda s: seen.append(len(s)) or [0.0] * 384)

    async def fake_llm(messages, model=None):
        return "ok"
    monkeypatch.setattr(main, "llm", fake_llm)
    client.post("/api/chat", json={"message": "zzqx " * 10_000})
    client.post("/api/chat", json={"message": "remember " + "y" * 50_000})
    assert seen and max(seen) <= routing.MAX_CHARS


def test_decide_clamps_p_and_uses_temperature_zero(monkeypatch):
    import httpx
    bodies = []

    def handler(req):
        bodies.append(__import__("json").loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": handler.out}}]})
    _decide_with(monkeypatch, handler)
    handler.out = '{"route": "email", "p": 7}'
    assert run(main.decide("x")) == ("email", 1.0)
    handler.out = '{"route": "email", "p": -1}'
    assert run(main.decide("x")) == ("email", 0.0)
    assert bodies[0]["temperature"] == 0
