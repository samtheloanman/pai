# PAI Audit Trail, Cryptographic Log Chain & PRD Synthesis

**Date:** 2026-11-01  
**Scope:** Tamper-Evident Audit Logging, SQLCipher Ledger, and Unified PRD v0.2 Synthesis  

---

## 1. Tamper-Evident Audit Trail Specification

### 1.1 Architecture & Cryptographic Hash Chain
To ensure zero covert agent operations, silent history rewriting, or unauthorized data leakage:
- **Hash-Chained Rows:** Each entry calculates `sha256(prev_hash + timestamp + event_type + payload_json)`:
  ```sql
  CREATE TABLE IF NOT EXISTS audit_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      prev_hash TEXT NOT NULL,
      current_hash TEXT NOT NULL,
      timestamp TEXT NOT NULL,
      event_type TEXT NOT NULL,   -- 'model_call', 'routing', 'agent_action', 'system_change', 'data_egress', 'memory_op'
      actor TEXT NOT NULL,        -- 'user', 'hermes', 'rakazo', 'router', 'system'
      risk_class TEXT,            -- 'read', 'send', 'delete', 'spend', 'system_change'
      confirmed_by TEXT,          -- 'owner', 'rule', 'none'
      payload_json TEXT NOT NULL
  );
  CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
  ```
- **Storage Isolation:** Stored in `/var/pai/audit.db` (encrypted with SQLCipher), completely distinct from `/var/pai/pai.db`. Chat history wipes **never** purge the audit trail, and vice versa.
- **Verification Routine:** A lightweight verification function traverses the table in `O(N)` time to assert that every `prev_hash` matches the preceding `current_hash`. Any manual deletion, truncation, or row update breaks the chain and triggers an alert on the UI.

### 1.2 Unified Ingestion Interface
Every component interacts via a single synchronous Python function:
```python
def audit(event_type: str, actor: str, payload: dict, risk_class: str = None, confirmed_by: str = None) -> str:
    # Inserts row, computes SHA256 chain, writes to /var/pai/audit.db
```
- **LiteLLM Integration:** Implemented as a custom LiteLLM logging callback (`CustomLogger` class in Python). Bypasses heavy PostgreSQL spend-tracking requirements.
- **Privacy Guarantee (Default-Zero-Content):** Raw prompt strings and model completions are **never** logged unless the owner toggles explicit content logging with a 30-day auto-purge TTL. Only metadata (tokens, model name, masked fields, egress IP/domain, latency) is recorded.

---

## 2. Recommendation: Yes, Update the PRD in One Unified Pass

We have collected and validated all core architectural requirements across today's sessions:
1. **Base OS Foundation:** Immutable, transactional `bootc` (Fedora/CentOS Stream base) with A/B rollback, zero open WAN ports, and pre-update DB snapshot hooks (`docs/LLM-COUNCIL-BASE-OS.md`).
2. **Multi-Tier Routing Engine:** Tier 0 (deterministic hard gates) -> Tier 1 (fast 80MB C++ embedding match) -> Tier 2 (Kev-pattern typed decision prompt) -> LiteLLM dispatch (`docs/ROUTING-AND-PAIR.md`).
3. **App Replacement Engine:** REA, reverse-api-engineer, api-anything, CLI-Anything, and anythingmcp packaged as declarative MCP tools in ephemeral Podman sandboxes (`docs/APP-REPLACEMENT-ENGINE.md`).
4. **Autonomous Agent Core:** Hermes (local reasoning & background execution) + Rakazo (persistent browser automation).
5. **Decentralized Storage & Sync:** Syncthing for zero-cloud device sync; Storj / Rclone Crypt for zero-knowledge offsite backup.
6. **Network Security Engine (LAN Guardian):** Passive ARP real-time listener, DoH interception, Unbound sinkhole, and Lynis auditing (`docs/NETWORK-SECURITY-ENGINE.md`).
7. **Tamper-Evident Audit Trail:** Hash-chained SQLCipher ledger recording every model call, routing choice, confirmed action, and cloud egress event.

---

## 3. Direct Response to Claude

```markdown
1. Audit Trail: Approved.
   - Hash-chained SQLite table (`prev_hash` -> `current_hash`) in `/var/pai/audit.db`.
   - Default-zero-content: Record metadata, tokens, masked fields, and destinations; raw prompt logging is opt-in.
   - Wire via custom LiteLLM Python callback and a single unified `audit()` function.
2. PRD Update: YES, let's roll all new requirements into PRD v0.2 in one clean pass now:
   - Base OS: bootc container-native immutable base + greenboot A/B rollback.
   - Routing: Tier 0 regex -> Tier 1 embeddings -> Tier 2 typed prompt -> LiteLLM / PAIR.
   - App Replacement: REA / CLI-Anything / api-anything / anythingmcp as sandboxed MCP tools.
   - Autonomous Agents: Hermes + Rakazo.
   - LAN Security: Passive ARP discovery + DNS sinkhole + Lynis.
   - Decentralized Sync: Syncthing + Storj/Rclone Crypt.
   - Tamper-Evident Audit Trail: Hash-chained SQLCipher ledger.
```
