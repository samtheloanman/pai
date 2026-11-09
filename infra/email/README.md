# Runbook: project email routing

Sets up the project addresses on Cloudflare Email Routing. Not live yet: it waits for the PAI domain.

| Address | Goes to | How |
|---|---|---|
| `agents@<domain>` | `pai-inbox` Worker → `<maintainer-inbox>` with `X-PAI-Request-Type` | Email Worker rule |
| `security@<domain>` | `pai-inbox` Worker → `<maintainer-inbox>` tagged `security` | Email Worker rule |
| `list@<domain>` | `pai-dev@googlegroups.com` | Forward rule |
| everything else | drop | Catch-all: drop |

## Prerequisites
- The PAI domain is registered and its DNS is on Cloudflare (zone active).
- Cloudflare access with Email Routing and Workers edit rights.
- `<maintainer-inbox>` verified as a destination address (Cloudflare sends a verification email).
- The Google Group `pai-dev` exists and accepts posts from non-members (Group settings → Posting permissions), so `list@` forwards land.

## Steps
1. **Test the classifier:** `cd infra/email && npm test`.
2. **Enable Email Routing:** Dashboard → the domain → Email → Email Routing → *Enable*. Accept the MX and SPF records it adds. Check no other mail provider's MX records are on the domain first.
3. **Verify destinations:** Email Routing → Destination addresses → add `<maintainer-inbox>` and `pai-dev@googlegroups.com`; click the links Cloudflare emails.
4. **Deploy the Worker:** `cd infra/email && npx wrangler deploy`.
5. **Rules:** Email Routing → Routing rules:
   - `agents@` → *Send to a Worker* → `pai-inbox`
   - `security@` → *Send to a Worker* → `pai-inbox`
   - `list@` → *Send to an email* → `pai-dev@googlegroups.com`
   - Catch-all → *Drop*
6. **Replace `pai.example`** with the real domain in `CONTRIBUTING.md`, `SECURITY.md` and `docs/agent-workflows/`.

## Verify
- Send `[install] test` to `agents@<domain>`. It arrives at `<maintainer-inbox>`; the raw headers show `X-PAI-Request-Type: install`.
- Send `test` to `security@<domain>` → `X-PAI-Request-Type: security`.
- Send to `list@<domain>` → the post appears in the Google Group.
- `npx wrangler tail pai-inbox` shows each message while you test.

## Rollback
Disable the routing rule (or Email Routing) for the domain in the dashboard. `npx wrangler delete pai-inbox` removes the Worker. Mail then bounces instead of being lost silently.

## Gmail filters (optional)
Filter on `X-PAI-Request-Type` is not possible in Gmail; filter on `to:agents@<domain>` and the subject tag instead, e.g. label `PAI/install` for `subject:[install]`.

Set the forward address as a secret, not in `wrangler.toml`: `npx wrangler secret put FORWARD_TO`.
