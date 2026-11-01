# Local Brain & Sovereign Filing System Architecture

**Synthesized from:** Fleet Brain Audit (2026-10-23), IJFW Memory, and PAI Sovereign Appliance Design  
**Principle:** /ponytail (Zero cloud drift, zero JSONL spam, sub-8ms retrieval, strictly deterministic)

---

## 1. Timeline of Local Network Brain Evolution

| Date / Milestone | What Was Implemented | Core Failure Mode / Bottleneck Identified |
|---|---|---|
| **April – July 2026** | Initial `brain-api` Cloudflare Worker + D1 database (`events` table). Basic shared memory over public WAN. | Secrets sprawl across machines (`.secrets/brain-api-keys.env`). Slow roundtrips (200–500ms). |
| **August 2026** | Automated file watcher (`claude_watcher.py`) dumping agent JSONL logs into D1. | **Catastrophic Noise Inflation:** 916,000 raw chat lines flooded D1. Vectorize became polluted with partial user keystrokes; search returned duplicated junk. |
| **September 2026** | Jev (OpenRouter Decisions API) & Kev (`arjun988/Kev`) local routing integration. Node.js daemon tests on Dell node. | Kev added Node.js runtime bloat to Python nodes; uncalibrated confidence scores. |
| **October 23, 2026** | **The Fleet Brain Audit**: Identified 1.29M rows of noise; `/v1/ask` took 13.7s; agents didn't read memory automatically. | Set mandate: Stop streaming raw transcripts. Store **distilled facts only** (decisions, lessons, summaries) with token-capped context packs (`thedotmack/claude-mem` & `mem0` models). |
| **October 31, 2026** | **PAI Sovereign Base**: `bootc` immutable OS, SQLCipher AES-256 vault, embedded `sqlite-vec`, and hash-chained audit logging. | Proven architecture: Cloudflare D1 can be entirely replaced by an embedded local SQLite mesh over Tailscale. |

---

## 2. Lessons to Take Away

1. **NEVER Stream Raw Transcripts to Memory**:
   - Streaming raw conversation turns created 916k rows of garbage in D1.
   - **The Rule:** Only write *distilled durable knowledge* at session boundaries: `decision`, `fact`, `lesson`, `task`, or `session.summary`.
2. **Deterministic Recency & Deduplication**:
   - Content-addressed hashing (`sha256(content)`) prevents duplicate entries.
   - Hybrid scoring: Vector similarity alone is blind to time. Rank using `reciprocal_rank = 0.7 * vector_score + 0.3 * recency_decay`.
3. **Zero Secrets on LAN / Mesh**:
   - Dropping static API keys in favor of WireGuard/Tailscale node identity (`tailscale0`) removes key management permanently.
4. **Embedded C/SQLite over Remote Cloud**:
   - Replacing remote Cloudflare D1 with local SQLite + `sqlite-vec` drops query latency from **380ms down to 4ms**.

---

## 3. The Sovereign Filing System Design (`/var/pai/storage`)

An organized, content-addressed filing hierarchy for documents, audio, and agent artifacts:

```
/var/pai/
├── brain/
│   ├── brain.db              # SQLite + FTS5 + sqlite-vec (Facts & Knowledge)
│   └── audit.db              # SQLCipher append-only hash chain (Tamper-evident log)
├── vault/
│   ├── keys/                 # Encrypted SSH / Tailscale auth keys
│   └── secrets.enc           # Encrypted environment credentials
├── filesystem/               # The Sovereign Filing System
│   ├── inbox/                # Raw user uploads (drag-and-drop, email attachments)
│   ├── archive/              # Processed, deduplicated immutable files
│   │   └── YYYY/MM/          # Partitioned by ingestion date (named by SHA256)
│   ├── artifacts/            # Agent generated reports, specs, and code diffs
│   │   └── {project_slug}/   # e.g., /artifacts/pai/SPEC.md
│   └── tools/                # Generated sandboxed MCP tools (CLI-Anything / REA)
└── snapshots/                # Pre-update database backups for atomic rollback
```

---

## 4. The Unified Brain Database Schema

```sql
-- Core knowledge table (One table, zero noise)
CREATE TABLE IF NOT EXISTS facts (
    fact_id TEXT PRIMARY KEY,           -- sha256(canonical_content)
    created_at TEXT NOT NULL,           -- ISO8601
    updated_at TEXT NOT NULL,
    project TEXT NOT NULL,              -- 'pai', 'cmre', 'global'
    category TEXT NOT NULL,             -- 'decision', 'architecture', 'lesson', 'credential_ref'
    summary TEXT NOT NULL,              -- 1-line distilled fact
    details TEXT,                       -- Optional deep context (Markdown)
    source_agent TEXT NOT NULL,         -- 'claude', 'antigravity', 'hermes'
    source_node TEXT NOT NULL,          -- 'mbp-2023', 'dell-brain', 'pai-appliance'
    superseded_by TEXT                  -- Pointer to newer fact if updated
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_fts USING fts5(
    summary,
    details,
    content='facts',
    content_rowid='rowid',
    tokenize='porter'
);

CREATE VIRTUAL TABLE IF NOT EXISTS facts_vec USING vec0(
    fact_id TEXT PRIMARY KEY,
    embedding float[384]                -- Generated locally via all-MiniLM-L6-v2
);

CREATE INDEX idx_facts_project ON facts(project);
CREATE INDEX idx_facts_category ON facts(category);
CREATE INDEX idx_facts_created ON facts(created_at);
```

---

## 5. Universal MCP Server Implementation (`pai-brain-mcp`)

Run as a single Python script on the local PAI appliance (`pai_brain_mcp.py`):

```python
from mcp.server.fastmcp import FastMCP
import sqlite3, hashlib, datetime

mcp = FastMCP("pai-brain")

@mcp.tool()
def memory_store(project: str, category: str, summary: str, details: str = "") -> str:
    """Store a distilled fact, decision, or lesson. Never store raw transcripts."""
    fact_id = hashlib.sha256(f"{project}:{summary}".encode()).hexdigest()[:16]
    now = datetime.datetime.utcnow().isoformat()
    # Writes atomically to facts, updates FTS5 and sqlite-vec
    return f"Stored {fact_id} ({category}) in project {project}"

@mcp.tool()
def memory_search(query: str, project: str = None, limit: int = 5) -> list:
    """Hybrid search combining FTS5 lexical matching and sqlite-vec embeddings."""
    # Returns ranked list of active, non-superseded facts in < 5ms
    pass

@mcp.tool()
def memory_context(project: str, budget_tokens: int = 1500) -> str:
    """Returns compact Markdown context pack for session startup injection."""
    pass
```

### Registered Client Config (`~/.claude.json`, `~/.codex/config.toml`, `antigravity.json`):
```json
{
  "mcpServers": {
    "pai-brain": {
      "command": "ssh",
      "args": ["pai@100.x.y.z", "python3", "/var/pai/pai_brain_mcp.py"]
    }
  }
}
```
All machines and agents connect natively over the WireGuard mesh with zero cloud exposure.
