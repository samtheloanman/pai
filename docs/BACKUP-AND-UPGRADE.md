# Backing up, restoring and upgrading PAI

Everything PAI knows about you lives in two encrypted files in the `data` volume: `pai.db` (profile, rules, memories, approvals, login) and `audit.db` (the activity log). Both are locked with the **vault key**. A backup without the key cannot be opened by anyone, including you.

Commands below run from `prototype/`. `scripts/pai-backup` starts containers through `scripts/pai-up`, so it uses the same key you start PAI with.

## 1. Back up the vault key (once)

Do this first. Without the key there is no recovery.

| Where the key lives | How to copy it out |
|---|---|
| macOS Keychain (`scripts/pai-up new-key` or `import-key`) | `security find-generic-password -s pai-vault-key -w` |
| `.env` or `~/.config/pai/vault-key` | copy the `PAI_VAULT_KEY=` value, or the file |

Store it in a password manager, or on paper in a safe place. Keep it apart from your backups: whoever has both can read everything.

## 2. Back up your data

```bash
scripts/pai-backup backup ~/pai-backups        # safe while PAI is running
scripts/pai-backup verify ~/pai-backups/pai-backup-YYYYMMDD-HHMMSS.tar
```

- One `.tar` file per backup, permissions `600`. The files inside stay encrypted.
- `verify` opens the backup with your current key, counts memories and checks the activity log has not been altered.
- Copy the `.tar` somewhere off the box (external drive, another machine). Keep more than one.

## 3. Restore a backup

```bash
scripts/pai-backup restore ~/pai-backups/pai-backup-YYYYMMDD-HHMMSS.tar
```

It verifies the backup first and stops if your key does not open it. Then it stops the app, swaps the files in and starts the app again. The files it replaced are kept in the data volume under `pre-restore-<time>/`; nothing is deleted. Your owner passphrase and paired devices become whatever they were at the time of the backup.

A backup made by a newer PAI is refused. Update PAI first.

## 4. Move your data to another box, or bring it in from elsewhere

Use export and import when the vault key is different (a new box) or you only want your content, not logins:

```bash
scripts/pai-backup export ~/pai-export.json          # on the old box
scripts/pai-backup import ~/pai-export.json          # on the new box
scripts/pai-backup import ~/pai-export.json --replace   # also overwrite profile answers and rules
```

- The export holds your profile answers, rules and memories. It leaves out the passphrase, sessions, devices and pending approvals.
- **The export is not encrypted.** Move it directly, then delete it.
- Import adds memories that are not already there and keeps what the box already has, unless you pass `--replace`.

## 5. After merging PRs #11, #12 and #13

Do these once, in order, on the machine that runs PAI.

1. **Back up before you upgrade.** Steps 1 and 2 above. The upgrade changes the vault's format, and an older PAI cannot open the new format. The backup you take now is your way back.
2. **Update and rebuild.**
   ```bash
   cd ~/Code/pai && git checkout main && git pull
   cd prototype && scripts/pai-up --profile local up -d --build
   ```
   The images are now pinned by digest, so the first start pulls them again.
3. **Create the owner passphrase.** Open `http://127.0.0.1:8088` on that machine. Until you do, the first person to open the app becomes its owner. At least 12 characters; there is no reset.
4. **Check the outbound lock.** If you use a cloud model, turn it on again in Runtime and send one message. LiteLLM can now reach only the providers you turned on. In OpenRouter setup mode also set `PAI_EGRESS_ALLOW=openrouter.ai` in `.env`.
5. **Publish to your phone (optional).** On a Linux box: `sudo ./setup-pai-vpn-gateway.sh up`, then `sudo ./setup-pai-vpn-gateway.sh serve`, then `./verify-vpn-tunnel.sh`. If you ran the old version of the setup script, run `sudo ./setup-pai-vpn-gateway.sh down` first: it removes the exit node, LAN routes and NAT rules the old version added.
6. **Pair your phone.** Devices tab → "Pair a new device". On the phone open the box's private address → "Pair with a code instead" → enter the code.
7. **Take a fresh backup** now that the owner and devices exist.

### Going back

To roll back: run the older PAI version and restore the backup from step 1 (`scripts/pai-backup restore`). The older version refuses the upgraded vault, so the restore is required, and anything added after the upgrade is lost unless you export it first.

## Known limits

- No scheduled backups yet; run `backup` yourself or from cron.
- No passphrase change or reset yet. A forgotten passphrase means restoring a backup from before you set it, or starting a new vault and importing an export.
