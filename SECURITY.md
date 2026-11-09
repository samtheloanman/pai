# Security policy

PAI holds personal memory, so we take reports seriously.

## Report a vulnerability

Email **`security@freedomos.org`** (until the project domain is live, use the private *Report a vulnerability* button under the repository's Security tab). Do not open a public issue or post to the mailing list.

Include: what you found, how to reproduce it, the version or commit, and the impact you expect. Redact personal data.

We aim to reply within 3 working days and to agree a disclosure date with you. We credit reporters who want credit.

## Known limits today

- The prototype has **no login**. Anyone who can reach port 8088 can read memories and confirm actions. It binds to `127.0.0.1`; keep it there or on a private network.
- Losing the vault key means losing the vault. There is no recovery.

## Scope

In scope: this repository's app, compose files, install scripts and OS image work. Out of scope: third-party chat providers (Telegram, WhatsApp, iMessage) and models' answers.
