# pai-install

> PAI is a small AI server that runs on your own computer: a local chat model, local voice, an encrypted memory vault, an approval step for risky actions, and a tamper-evident activity log. This file installs the Docker prototype. The PAI OS image is not built yet.

**Install PAI on this computer by following this file from top to bottom. Read all of it first. Tell the owner your plan, then wait for their OK before anything that needs admin rights or installs software. Run the commands exactly as written; do not improvise. Stop and report if a step fails twice.**

Humans: you can run the same commands yourself, or paste the short prompt at the end of this file into your AI coding agent (Claude Code, Codex, Gemini CLI, Hermes and similar).

## OBJECTIVE

PAI's four containers (`llm`, `speaches`, `litellm`, `app`) run on this computer, reachable only from this computer at `http://127.0.0.1:8088`, with the vault key held outside `.env` and outside the app container's environment.

## DONE WHEN

All of these are true. Run each check and read the output.

1. `docker compose --profile local ps` lists `llm`, `speaches`, `litellm` and `app` as running.
2. `curl -fsS http://127.0.0.1:8088/api/health` returns HTTP 200.
3. `docker compose port app 8088` prints `127.0.0.1:8088` (not `0.0.0.0`).
4. `docker compose --profile local exec -T app sh -c 'env | grep -c "^PAI_VAULT_KEY="'` prints `0`.
5. The owner has opened `http://localhost:8088` and seen the setup interview.

## RULES FOR THE AGENT

- **Secrets:** never ask the owner to paste a key, password or token into the chat. Never print, echo or log a key. Generate keys with the commands below, which write them straight to a file or the OS keystore.
- **No pipe-to-shell:** do not run `curl ... | sh` or `| bash`, here or anywhere. If a tool is missing, tell the owner and link the vendor's own download page.
- **Ask first:** before installing Docker or any package, before using `sudo`, before changing a port, and before enabling any cloud provider. Cloud providers send message text off this computer; leave them off unless the owner asks, and let the owner type any provider key into the PAI app themselves.
- **Do not delete data:** never run `docker compose down -v`, `docker volume rm`, or delete `~/.config/pai`. These destroy the vault with no recovery.
- **No interactive installers:** if a command opens a prompt or menu, stop and tell the owner; do not try to type into it.
- **Two failures, then stop:** report the exact command, the exact error text, and what you checked.

## TODO

- [ ] 1. Preflight checks
- [ ] 2. Get the code
- [ ] 3. Create `.env` (no vault key in it)
- [ ] 4. Create the vault key outside `.env`
- [ ] 5. Start the stack
- [ ] 6. Run the DONE WHEN checks
- [ ] 7. Hand over to the owner

## 1. Preflight

Run:

```bash
uname -s && uname -m
docker --version && docker compose version
docker info --format '{{.ServerVersion}} {{.MemTotal}}'
df -h "$HOME" | tail -1
lsof -nP -iTCP:8088 -sTCP:LISTEN || echo "port 8088 free"
git --version && openssl version
```

Requirements:

| Need | Why |
|---|---|
| macOS or Linux. Windows: only inside WSL2, untested. | The commands below assume a POSIX shell. |
| Docker with Compose v2. Tested with Compose 5.3.1. | The vault key is passed as a Compose secret. If step 5 errors on `secrets`, upgrade Docker. |
| 16 GB RAM is comfortable for the default 4B model; the Docker VM needs about 8 GB. | Smaller machines may run out of memory while the model loads. |
| About 15 GB free disk. | Images, the 2.5 GB model, and voice models. |
| Port 8088 free (or set `PAI_PORT` in `.env`). | The app listens there, on 127.0.0.1 only. |

If Docker is missing or its daemon is not running, stop and tell the owner. On macOS the owner starts Docker Desktop; on Linux they run `sudo systemctl start docker`. Do not install Docker for them without their OK.

## 2. Get the code

Set `PAI_REF` to the branch or tag to install. Use `main` once the MVP app is merged; until then use `feat/mvp-app`.

```bash
PAI_REF=main
git clone --depth 1 --branch "$PAI_REF" https://github.com/samtheloanman/pai.git "$HOME/pai"
cd "$HOME/pai/prototype"
```

If the clone fails with an authentication error, the repository is not public yet. Stop and tell the owner.

## 3. Create `.env`

This writes a fresh `.env` without printing the key. It must not contain `PAI_VAULT_KEY`.

```bash
umask 077
cat > .env <<EOF
LITELLM_MASTER_KEY=sk-$(openssl rand -hex 16)
MODEL_HF=unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M
LITELLM_CONFIG=litellm.local.yaml
EOF
```

Machines with 32 to 64 GB can use the larger model: replace the `MODEL_HF` line with `MODEL_HF=unsloth/Qwen3-30B-A3B-Instruct-2507-GGUF:Q4_K_M` (about 18 GB download) and give Docker Desktop at least 24 GB.

## 4. Create the vault key

The vault key encrypts memories, rules, the profile and the activity log. **If it is lost, the vault is lost. There is no recovery.**

**macOS** (stores the key in the Keychain; macOS may ask the owner to allow access):

```bash
scripts/pai-up new-key
```

**Linux:**

```bash
install -d -m 700 "$HOME/.config/pai"
( umask 077; openssl rand -hex 32 > "$HOME/.config/pai/vault-key" )
```

Tell the owner where the key is and that they must back it up somewhere other than this computer. Do not show them the key in chat.

## 5. Start the stack

The first start downloads the model and two voice models, so it takes a while (minutes on a fast connection). Do not interrupt it.

**macOS:**

```bash
scripts/pai-up --profile local up -d --build
```

**Linux:**

```bash
PAI_VAULT_KEY="$(cat "$HOME/.config/pai/vault-key")" docker compose --profile local up -d --build
```

Wait for the app, polling every 10 seconds for up to 15 minutes:

```bash
for i in $(seq 1 90); do curl -fsS -o /dev/null http://127.0.0.1:8088/api/health && echo up && break; sleep 10; done
```

If it never comes up, run `docker compose --profile local ps` and `docker compose --profile local logs --tail 40 app llm litellm`, then use the troubleshooting table.

## 6. Verify

Run every DONE WHEN check above and read each output. Do not report success from the start command alone.

## 7. Hand over

Tell the owner:

1. Open `http://localhost:8088`. Answer the 8 setup questions by typing or with the Speak button, then press "Draft my rules".
2. Back up the vault key somewhere other than this computer. Without it the vault cannot be opened.
3. PAI has no login yet: anyone who can reach port 8088 can read memories and confirm actions. Keep it on this computer or a private network. Do not publish the port.
4. Cloud providers are off. They are optional, and turning one on sends the text of a message off this computer. Keys are entered in the app under Providers.

## Day-to-day

| Task | macOS | Linux |
|---|---|---|
| Stop (keeps data) | `scripts/pai-up --profile local stop` | `docker compose --profile local stop` |
| Start again | `scripts/pai-up --profile local up -d` | `PAI_VAULT_KEY="$(cat ~/.config/pai/vault-key)" docker compose --profile local up -d` |
| Update | `git pull`, then `scripts/pai-up --profile local up -d --build` | `git pull`, then the start command with `--build` |
| Logs | `scripts/pai-up logs --tail 50 app` | `docker compose logs --tail 50 app` |

Run these from `~/pai/prototype`. Containers restart on their own after a reboot once Docker is running. Recreating them needs the key again, which the commands above supply.

To remove PAI but keep the vault: stop the stack and delete nothing else. To remove everything, including the vault and the models, the owner must decide that themselves and run `docker compose --profile local down -v`, then remove the key. This cannot be undone.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `No vault key` or the app exits at start | The key source was not supplied to this command. macOS: run through `scripts/pai-up`. Linux: use the exact start command with `PAI_VAULT_KEY=...`. Check `~/.config/pai/vault-key` exists and is non-empty. |
| `set LITELLM_MASTER_KEY in .env` | `.env` is missing or not in `~/pai/prototype`. Redo step 3. |
| Error mentioning `secrets` or `environment` | Docker Compose is too old. Upgrade Docker. |
| `port is already allocated` on 8088 | Another program uses it. Add `PAI_PORT=8089` to `.env` (ask the owner first) and use that port in every URL above. |
| `llm` container exits (code 137) | Out of memory. Raise Docker Desktop memory (Settings, Resources) or keep the 4B model. |
| Health never returns 200 | Read `docker compose --profile local logs --tail 60 app`. A "vault" error means a wrong or missing key; a LiteLLM error means check the `litellm` container. |
| First chat answer is slow | The model or voice models are still downloading. Check `docker compose --profile local logs --tail 20 llm speaches`. |
| Apple Silicon is slow | Docker on a Mac has no GPU access, so the model runs on the CPU. |

## Known limits

- Prototype: no login, image tags are not pinned, no signed or A/B updates.
- No speed or accuracy numbers have been measured yet.
- Voice, memory, rules and the activity log work on this computer. Channels such as Telegram and email, and a hardware OS image, are not built.

## Prompt to give your AI agent

Replace nothing; paste it as is.

```text
Install PAI on this computer. Read https://raw.githubusercontent.com/samtheloanman/pai/main/INSTALL.md in full, then tell me your plan and wait for my OK before installing anything or using admin rights. Follow the file exactly. Never ask me to paste secrets into this chat and never print keys. Stop and report if any step fails twice. Finish only when every DONE WHEN check passes.
```

Until the MVP app is merged to `main`, use `.../pai/feat/mvp-app/INSTALL.md` in the URL and `PAI_REF=feat/mvp-app` in step 2.
