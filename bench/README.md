# pai-bench

Measures each box and upgrade stage. Implements BUILD-PLAN Track 2.

- Engine: llama.cpp `llama-bench` (Vulkan on AMD, CUDA on a dock GPU) plus a real chat replay.
- Models: Qwen3-30B-A3B Q4_K_M, gpt-oss-20b, a Gemma-class 12B, a 7-8B dense model; gpt-oss-120b on Pro.
- Metrics: prompt t/s at 512 and 4k tokens, decode t/s, time to first token, peak memory, wall watts (smart plug), noise at 1 m.
- Stages: base memory → full memory → + GPU dock → + second box (RPC).
- Output: one JSON per run in `results/`, plus `results/SUMMARY.md` that the store and campaign pages cite.
