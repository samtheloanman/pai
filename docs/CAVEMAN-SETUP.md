# Caveman Setup Guide (Zero-BS 1-Line Run)

Get PAI running on any laptop or mini PC with one command.

---

## 1-Line Magic Command

Run this in your terminal:

```bash
cd ~/Code/pai/prototype && ./setup.sh
```

*(Or manual 3-step)*:
```bash
cp .env.example .env
docker compose --profile local up -d --build
open http://localhost:8088
```

---

## What It Does (Automatic)
1. **Generates Keys**: Creates random `LITELLM_MASTER_KEY` and encrypted `PAI_VAULT_KEY` (SQLCipher AES-256).
2. **Starts Stack**: Boots `llm` (llama.cpp), `speaches` (Whisper + Kokoro), `litellm` gateway, and `app` (FastAPI + React).
3. **Healthcheck**: Loops until `localhost:8088/api/interview` returns HTTP 200.
4. **Opens Browser**: Launches the web UI directly to the setup interview.

---

## How to Use PAI

1. **First Boot**: Answer 8 questions (Type or tap **🎤 Speak**). Click **Draft my rules**.
2. **Chat**: Type or speak. Say *"remember that..."* to save permanent knowledge to your encrypted vault.
3. **Approvals**: Any risky action (sending email, deleting data, spending) pops an approval prompt with an expiration countdown.
4. **Activity**: View the append-only cryptographic audit chain on the Activity page.
5. **Memory**: Review, search, or forget memories in the Memory tab.
