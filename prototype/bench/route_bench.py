"""Route bench: POST labelled requests to a running app's /api/route and report accuracy and added latency.

    python bench/route_bench.py --base http://localhost:8088
"""
import argparse
import json
import math
import os
import time
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def load_cases(path: str = os.path.join(HERE, "route_cases.jsonl")) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def run(cases: list[dict], post) -> list[dict]:
    """post(text) -> {"route", "tier", "score"}. Times each call."""
    rows = []
    for c in cases:
        t0 = time.perf_counter()
        r = post(c["text"])
        rows.append({"text": c["text"], "route": c["route"], "got": r["route"], "tier": r["tier"],
                     "score": r["score"], "ms": (time.perf_counter() - t0) * 1000})
    return rows


def _pct(sorted_ms: list[float], p: float) -> float:
    if not sorted_ms:
        return 0.0
    k = (len(sorted_ms) - 1) * p
    lo, hi = math.floor(k), math.ceil(k)
    return sorted_ms[lo] + (sorted_ms[hi] - sorted_ms[lo]) * (k - lo)


def summarize(rows: list[dict]) -> dict:
    ok = lambda rs: sum(r["route"] == r["got"] for r in rs)  # noqa: E731
    per_tier = {}
    for t in sorted({r["tier"] for r in rows}):
        rs = [r for r in rows if r["tier"] == t]
        per_tier[str(t)] = {"n": len(rs), "correct": ok(rs), "accuracy": ok(rs) / len(rs)}
    ms = sorted(r["ms"] for r in rows)
    return {"n": len(rows), "correct": ok(rows), "accuracy": ok(rows) / len(rows) if rows else 0.0,
            "per_tier": per_tier, "latency_ms": {"p50": _pct(ms, 0.5), "p95": _pct(ms, 0.95)},
            "misses": [{k: r.get(k) for k in ("text", "route", "got", "tier")} for r in rows if r["route"] != r["got"]]}


def save(summary: dict, out_dir: str = os.path.join(HERE, "results")) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"route-{datetime.now():%Y%m%d-%H%M}.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    return path


def main() -> None:
    import httpx
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8088")
    a = ap.parse_args()
    with httpx.Client(base_url=a.base, timeout=300) as c:
        rows = run(load_cases(), lambda t: c.post("/api/route", json={"message": t}).raise_for_status().json())
    s = summarize(rows)
    print(json.dumps({k: v for k, v in s.items() if k != "misses"}, indent=2))
    print("saved", save(s))


if __name__ == "__main__":
    main()
