import json
import os
import sys

from fastapi.testclient import TestClient

import pytest  # noqa: E402

BENCH = os.path.join(os.path.dirname(__file__), "..", "..", "bench")
if not os.path.isdir(BENCH):  # the docker test runner mounts only app/
    pytest.skip("bench/ not mounted", allow_module_level=True)
sys.path.insert(0, BENCH)
import route_bench  # noqa: E402

import main  # noqa: E402


def test_summarize_accounting():
    rows = [
        {"route": "chat", "got": "chat", "tier": 1, "ms": 10},
        {"route": "email", "got": "chat", "tier": 2, "ms": 20},
        {"route": "email", "got": "email", "tier": 2, "ms": 30},
        {"route": "chat", "got": "chat", "tier": 3, "ms": 40},
    ]
    s = route_bench.summarize(rows)
    assert s["n"] == 4 and s["correct"] == 3 and s["accuracy"] == 0.75
    assert s["per_tier"]["2"] == {"n": 2, "correct": 1, "accuracy": 0.5}
    assert s["latency_ms"]["p50"] == 25 and s["latency_ms"]["p95"] <= 40


def test_cases_file_is_well_formed():
    cases = route_bench.load_cases()
    assert len(cases) >= 40
    counts = {}
    for c in cases:
        counts[c["route"]] = counts.get(c["route"], 0) + 1
    assert set(counts) == {"remember", "memory_query", "calendar", "email", "action", "chat"}
    assert min(counts.values()) >= 5


def test_run_against_testclient_with_fakes(tmp_path):
    tc = TestClient(main.app)
    cases = [{"text": "Remember that x", "route": "remember"}, {"text": "forget memory 1", "route": "action"}]
    out = route_bench.run(cases, lambda text: tc.post("/api/route", json={"message": text}).json())
    s = route_bench.summarize(out)
    assert s["n"] == 2 and s["accuracy"] == 1.0 and s["per_tier"]["1"]["n"] == 2
    p = route_bench.save(s, str(tmp_path))
    assert json.load(open(p))["n"] == 2


def test_cases_do_not_overlap_routing_examples_or_each_other():
    import re
    from pai import routing
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()  # noqa: E731
    examples = {norm(e) for es in routing.EXAMPLES.values() for e in es}
    seen = set()
    for c in route_bench.load_cases():
        n = norm(c["text"])
        assert n not in examples, f"overlaps an example: {c['text']}"
        assert n not in seen, f"duplicate case: {c['text']}"
        seen.add(n)
