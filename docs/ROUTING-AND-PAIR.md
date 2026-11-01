# PAI Multi-Tier Routing Architecture & NVIDIA PAIR Integration

**Date:** 2026-11-01  
**Scope:** Local Decision Routing (Kev/Semantic Router) vs. Multi-Node Distribution (NVIDIA PAIR)  
**PRD Alignment:** OS-5, OS-7, Privacy Guarantees, 16 GB Starter Limits  

---

## 1. Unified 3-Tier Routing Architecture

```
User Prompt (Voice / Text)
        │
        ▼
┌────────────────────────────────────────────────────────┐
│ Tier 0: Deterministic Guardrails & Hard Gates          │  <-- 0 ms (Zero tokens)
│ - Regex/keywords for 'remember', setup, rules          │
│ - Risky actions (spend/send/delete/system) MUST confirm│
└───────────────────────┬────────────────────────────────┘
                        │ (unhandled)
                        ▼
┌────────────────────────────────────────────────────────┐
│ Tier 1: Millisecond Semantic Route Matcher             │  <-- <5 ms (Local Embeddings)
│ - aurelio-labs/semantic-router                         │
│ - Exact intent clusters: calendar, notes, weather, chat│
└───────────────────────┬────────────────────────────────┘
                        │ (ambiguous / complex)
                        ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: Local Typed Decision Model (Kev Pattern)       │  <-- Local 1-3B Classifier
│ - Self-hosted typed decisions (choice, score, noul)    │
│ - Output is strictly JSON with calibrated probabilities│
│ - Low confidence on risky tasks -> Ask user to confirm │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│ Execution Dispatcher: LiteLLM + NVIDIA PAIR            │
│ 1. Single Node -> LiteLLM (:4000) local llama.cpp      │
│ 2. Multi-Box Node Mesh -> NVIDIA PAIR (PIN paired)     │
│ 3. Cloud (Opt-in only) -> Sanitized/Redacted via key   │
└────────────────────────────────────────────────────────┘
```

---

## 2. Decision Model: Kev vs. Alternatives

- **Kev (`arjun988/Kev`)**:
  - Apache-2.0 licensed, open-source local counterpart to OpenRouter Decisions (Jev).
  - Emits typed decisions with calibrated probability scores.
  - **Memory Footprint Concern on 16 GB Starter**: Adding a Node.js daemon and a second resident classifier model competes for VRAM/iGPU memory with the primary 4B/30B LLM.
  - **Clean Code Decision**: Re-implement the lightweight Kev decision prompt natively in Python within `app/router.py` (avoiding Node.js runtime overhead on headless PAI OS).

---

## 3. Multi-Node Mesh: NVIDIA Personal AI Router (PAIR)

- **Repository:** `NVIDIA/Personal-AI-Router` (Apache-2.0, released July 2026).
- **Function:** Distributes requests across multiple machines on a local network (e.g. PAI Starter 16 GB + Dell Quadro P3000 / Mac Pro GPU node).
- **Features:**
  - Auto-discovery and secure 6-digit PIN pairing.
  - Exposes standard OpenAI/Anthropic/Ollama endpoints.
  - Prompts remain strictly local within the home subnet.
- **Role in PAI Roadmap:**
  - **Step 4 of Hardware Upgrade Path** (PRD §5.2): PAI Starter routes heavy coding/vision/30B requests over LAN to a secondary GPU box or dock.
- **Disclaimers & Safety:**
  - Do NOT bundle closed-source installers (like LM Studio).
  - Clarify branding: PAI (our appliance) vs. NVIDIA PAIR (multi-node router).

---

## 4. Answers to Open Coordination Decisions

1. **Include small model in image or download on first boot?**
   - **Bake the 4B model into the base image.** PRD Goal 1 dictates <30 min unbox-to-answer with zero terminal and offline reliability.
2. **Same model or separate classifier?**
   - **Single model + Tier 1 Embedding Matcher.** Use Tier 1 semantic embeddings for speed, then use the already-loaded primary local model with structured JSON prompting for Tier 2 decisions. Prevents dual-model VRAM starvation on 16 GB hardware.
3. **Default cloud provider if user opts in?**
   - **None.** Privacy-first default: Zero data leaves the box unless the user explicitly inputs their own key.
4. **Testing PAIR now or hold?**
   - **Hold as Track 4 (Post-MVP multi-node feature).** Test between `mbp-2023` and `dell-precision` during the secondary node milestone.
