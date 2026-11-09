# Contributing to PAI

Thanks for helping. There are three ways in: the mailing list, the agent request inbox, and GitHub. Pick whichever suits you.

> Addresses below use `freedomos.org` until the project domain is registered. Replace it everywhere when it is live.

## 1. Mailing list (discussion)

The list is the place for questions, design talk, proposals and release notes. Plain text, old-school, archived.

- **Join:** send any email to `pai-dev+subscribe@googlegroups.com`, or open the group page and click *Join*.
- **Post:** `pai-dev@googlegroups.com` (alias: `list@freedomos.org`).
- **Archive:** the Google Group web page.

Etiquette:
- Plain text, no HTML. Reply inline, trim quotes, keep threads on topic.
- Subject tags: `[RFC]` proposal, `[Q]` question, `[ANN]` announcement, `[PATCH]` small fix as a diff.
- Do not post secrets, keys, personal data or full logs with private information. Redact first.

## 2. Agent request inbox (get something done)

Email **`agents@freedomos.org`** to file a request. An agent triages it using the matching workflow in [`docs/agent-workflows/`](docs/agent-workflows/) and a maintainer is notified.

Put the request type in square brackets at the start of the subject:

| Subject starts with | Use it for | Workflow |
|---|---|---|
| `[bug]` | Something is broken | [bug-report.md](docs/agent-workflows/bug-report.md) |
| `[install]` | Help getting PAI running | [install-help.md](docs/agent-workflows/install-help.md) |
| `[model]` | Choosing, adding or tuning a model | [model-request.md](docs/agent-workflows/model-request.md) |
| `[feature]` | A new capability | [feature-request.md](docs/agent-workflows/feature-request.md) |
| `[docs]` | A docs error or gap | [docs-fix.md](docs/agent-workflows/docs-fix.md) |

No tag? The message is filed as `general` and a human reads it.

**Security problems never go to the agent inbox or the list.** Email `security@freedomos.org`; see [SECURITY.md](SECURITY.md).

Example:

```
To: agents@freedomos.org
Subject: [install] llm container exits with code 137 on 16 GB Mac

OS: macOS 15.2, Apple M2, 16 GB
Docker Desktop 4.40, memory limit 8 GB
MODEL_HF: unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M
Command: scripts/pai-up --profile local up -d --build
Output of `docker compose --profile local ps`: (pasted, redacted)
```

## 3. GitHub (code)

1. Open or pick an issue at https://github.com/samtheloanman/pai/issues.
2. Fork, branch from `main` (`fix/…`, `feat/…`, `docs/…`).
3. Keep changes small and focused. Add or update a test for new logic.
4. Open a pull request that says what changed, why, and how you checked it.
5. A maintainer reviews. CI must be green before merge.

Rules for code and docs:
- No secrets in code, `.env` examples, logs or screenshots.
- Claims about speed, noise or power need a `pai-bench` result in `bench/results/`.
- Avoid hype words ("revolutionary", "100% private", "unhackable"); describe what it does.
- AI-assisted contributions are welcome. You are responsible for every line you submit.

## Code of conduct

Be kind, be specific, assume good faith. Harassment gets you removed from the list and the repo.
