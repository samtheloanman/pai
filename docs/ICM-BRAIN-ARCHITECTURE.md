# PAI Sovereign ICM Brain: Intelligent Context & Memory Architecture

**Designed for:** PAI Operating System  
**Synthesized from:** Mem0 (Fact Extraction), Letta (OS Memory Paging), Zep/Graphiti (Temporal Validity), and MemPalace (Spatial Organization).  
**Implementation Standard:** /ponytail (Embedded C/SQLite, zero external vector DBs, sub-8ms retrieval, zero cloud reliance).

---

## 1. What to Steal from the Top Open-Source Projects

| Project | Core Superpower | What We Steal for PAI ICM Brain | What We Reject (Bloat/Risk) |
|---|---|---|---|
| **Mem0** | Fact Extraction & Personalization | Extract atomic facts/preferences (`add`, `update`, `delete`, `noop`) instead of raw chat turns. | Reject external cloud dependencies and heavy multi-tenant schema overhead. |
| **Letta** (MemGPT) | OS-Inspired 3-Tier Virtual Memory | Tiered context management: **Core** (in prompt), **Recall** (working session), and **Archival** (deep vector search). | Reject complicated LLM self-editing loops that waste tokens; manage paging deterministically. |
| **Zep / Graphiti** | Temporal Knowledge Graphs | **Fact succession & validity intervals** (`valid_from`, `valid_to`, `superseded_by`). | Reject Neo4j/Cypher database requirements; build graph edges into native SQLite relational tables. |
| **MemPalace** | Spatial Organization & Local Privacy | Spatial categorization ("wings", "rooms", "drawers") for instant project/topic scoping. | Reject unpruned verbatim chat history storage. |

---

## 2. The 3-Tier Architecture of the PAI ICM Brain

```
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 1: Core Memory (In-Context RAM - 1,500 tokens)                    │
│ • Owner profile & household rules (from first-boot interview)          │
│ • Active project context block (pinned decisions)                      │
│ • Instant injection on every turn (0 ms latency)                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (unresolved)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 2: Working Recall (Working Cache - Session Scope)                 │
│ • Short-term conversational thread & tool execution receipts           │
│ • Ephemeral SQLite table with automatic 7-day sliding window TTL       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ (unresolved)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ Tier 3: Archival Brain (Deep Storage - SQLCipher + sqlite-vec)         │
│ • Temporal Knowledge Graph (facts with validity dates)                 │
│ • Hybrid Search: FTS5 keyword index + 384-dim vector embeddings        │
│ • Content-addressed file vault (/var/pai/storage/archive/)             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The ICM Database Schema (`/var/pai/brain.db`)

Built natively in SQLite using SQLCipher (AES-256) and `sqlite-vec`:

```sql
-- 1. Atomic Facts & Temporal Knowledge
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,               -- sha256(canonical_fact_text)
    category TEXT NOT NULL,            -- 'identity', 'rule', 'decision', 'preference', 'project'
    project TEXT NOT NULL,             -- 'pai', 'cmre', 'home', 'general'
    subject TEXT NOT NULL,             -- e.g. 'router_ip', 'dentist_name', 'wifi_psk'
    predicate TEXT NOT NULL,           -- e.g. 'is', 'schedule_at', 'prohibits'
    object TEXT NOT NULL,              -- e.g. '192.168.1.1', 'Dr. Lee', 'cloud_backup'
    valid_from TEXT NOT NULL,          -- ISO8601 timestamp
    valid_to TEXT,                     -- NULL if currently active
    superseded_by TEXT,                -- Pointer to replacement fact_id
    confidence REAL DEFAULT 1.0,
    source_agent TEXT NOT NULL         -- 'user', 'hermes', 'claude'
);

-- 2. Hybrid Search Indices
CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    subject, predicate, object, category, project,
    content='facts', content_rowid='rowid'
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_vec USING vec0(
    id TEXT PRIMARY KEY,
    embedding float[384]               -- all-MiniLM-L6-v2 embeddings
);

-- 3. Spatial Rooms (MemPalace style scoping)
CREATE TABLE IF NOT EXISTS rooms (
    room_id TEXT PRIMARY KEY,          -- 'home/network', 'finance/taxes', 'code/pai'
    description TEXT,
    parent_room TEXT
);
```

---

## 4. How the ICM Brain Resolves and Evolves Knowledge

### Scenario A: Fact Evolution (Zep Pattern)
- **Day 1:** User says *"My dentist is Dr. Smith on Tuesdays"*.
  - Insert: `[F1] subject='dentist', object='Dr. Smith on Tuesdays', valid_from='2026-11-01', valid_to=NULL`.
- **Day 90:** User says *"I switched dentists to Dr. Lee on Fridays"*.
  - Update: Set `[F1].valid_to = '2026-12-01'`, `[F1].superseded_by = 'F2'`.
  - Insert: `[F2] subject='dentist', object='Dr. Lee on Fridays', valid_from='2026-12-01', valid_to=NULL`.
- **Result:** PAI always retrieves the active fact (`valid_to IS NULL`), while preserving the full temporal audit trail.

### Scenario B: Zero-Token Working Memory Injection (Letta Pattern)
- When a session opens for project `pai`, the PAI ICM daemon runs:
  ```sql
  SELECT subject, predicate, object FROM facts 
  WHERE project IN ('pai', 'global') AND valid_to IS NULL AND category IN ('identity', 'rule', 'decision')
  ORDER BY valid_from DESC LIMIT 15;
  ```
- Formats a compact 500-token markdown block injected into the system prompt:
  ```markdown
  [PAI Sovereign Memory]
  - Owner: Sam
  - Rule: Never email anyone without explicit confirmation.
  - Decision: Base OS is bootc with greenboot rollback.
  - Decision: Vault uses SQLCipher with FTS5 and sqlite-vec.
  ```
- **Zero search latency, zero external API calls.**
