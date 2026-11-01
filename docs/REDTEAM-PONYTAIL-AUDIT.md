# Red-Team Critique: Ponytail Simplification & Failure-Mode Analysis

**Target:** Ponytail Minimalist Architecture for PAI Appliance  
**Role:** Adversarial Security & Reliability Red Team  
**Objective:** Uncover hidden trade-offs, operational failure modes, and blind spots before Council review.

---

## 1. Attack Vectors & Operational Vulnerabilities in Ponytail Plan

### 1.1 "Single Model JSON Prompting" for Intent Routing (The Latency & Head-of-Line Trap)
- **The Ponytail Premise:** Delete external router daemons (Kev/Node.js); prompt the primary 4B/30B LLM for structured JSON routing.
- **Red-Team Finding:** 
  - **Head-of-Line Blocking:** If a user is streaming a long voice reply or writing a memo, prompting the primary `llama.cpp` instance for routing will either block the existing generation or queue the prompt behind it, introducing **1.5s to 3s latency** for simple commands like "what time is it?".
  - **Context Cache Eviction:** Swapping prompts between router system prompts and user conversation context constantly invalidates KV-cache pages in `llama.cpp`.
- **Recommended Hardening:** Keep Tier 0 (regex) and Tier 1 (fast local embeddings like `all-MiniLM-L6-v2` taking 80MB RAM in C++). Only escalate to the primary LLM when the system is idle.

### 1.2 "One-Shot App Cloners" (The Environment Breakage & Sandboxing Hole)
- **The Ponytail Premise:** Eliminate running microservices for REA, CLI-Anything, and api-anything; run them as on-demand one-shot subcommands outputting `.py` tools to `/var/pai/tools`.
- **Red-Team Finding:**
  - **Dependency Hell / Poisoning:** Running dynamically generated Python scripts directly in the host or app daemon risks dependency collisions, arbitrary code execution, or monkey-patching core PAI memory databases.
  - **Site Churn / Fragility:** Reverse-engineered APIs break without continuous session renewal or self-healing proxies. If an API breaks mid-execution without a background proxy holding refresh tokens, the assistant fails abruptly.
- **Recommended Hardening:** Store tool definitions as declarative JSON schemas (OpenAPI / MCP format). Execute tool implementations in ephemeral, read-only root Podman container sandboxes without access to `/data/pai.db`.

### 1.3 "Scheduled Nmap + Unbound Blocklist" as LAN Security (The Evasion & Alert Fatigue Hole)
- **The Ponytail Premise:** Replace Suricata, Zeek, and Wazuh with native `nftables`, `unbound` DNS sinkhole, and a 12-hour `nmap` sweep.
- **Red-Team Finding:**
  - **Blind to Direct-IP & Encrypted Exfiltration:** DNS sinkholing (`unbound`) misses malware that hardcodes direct IP addresses or uses DNS-over-HTTPS (DoH). Without light packet inspection or connection tracking, a compromised smart plug talking directly to an external command-and-control server on port 443 goes completely undetected.
  - **12-Hour Blind Spot:** An attacker or rogue device connecting at 2:05 AM and exfiltrating data for 20 minutes is never seen by a twice-daily nmap cron.
  - **Active Scan Triggers:** Running `nmap -sn` on some consumer routers triggers flood protection or freezes low-spec IoT firmware (e.g. cheap smart bulbs crash on port sweeps).
- **Recommended Hardening:** Avoid active aggressive port sweeps. Use passive ARP/NDP listening (`arpwatch` or passive packet socket) which detects new MACs in real time with zero network overhead. Block outbound DoH IPs and redirect all DNS ports to local `unbound`.

### 1.4 `bootc` Atomic Rollback (The Split-Brain State & Database Schema Drift Trap)
- **The Ponytail Premise:** Use `bootc` for transactional OCI root upgrades; if boot fails, the bootloader automatically reverts.
- **Red-Team Finding:**
  - **State vs. OS Drift (Database Split-Brain):** While `/usr` rolls back atomically, `/var/pai/pai.db` does not roll back with it. If version N+1 migrated the SQLite schema or added encrypted fields, and the box rolls back to version N due to a network glitch, version N crashes immediately on the newer database schema.
- **Recommended Hardening:** Enforce strict forward-compatible database migrations, or require pre-upgrade SQLite snapshot checkpoints: before `bootc switch`, snapshot `/var/pai/pai.db` to `/var/pai/pai.db.bak-v{current}`. If systemd triggers a rollback, automatically restore the corresponding database checkpoint.

---

## 2. Hardened Architecture for Expert LLM Council Review

| Layer | Ponytail Shortcut | Vulnerability / Failure Mode | Hardened Council Synthesis |
|---|---|---|---|
| **Routing** | Primary LLM JSON | Blocks active inference, high latency | Regex + 80MB C++ fast embeddings; primary model only on idle fallback |
| **App Cloner** | Unsandboxed `.py` scripts | Code execution risk, unhandled dependency breaks | Declarative MCP JSON schemas executed in ephemeral Podman sandboxes |
| **LAN Security** | 12h Nmap cron + DNS sink | Misses direct-IP malware, 12h detection lag | Passive ARP/NDP listener (real-time) + outbound DoH intercept + DNS sinkhole |
| **OS & DB Rollback** | `bootc` root rollback only | SQLite schema mismatch after OS rollback | Pre-update DB snapshot coupled to ostree deployment generation |
