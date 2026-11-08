# App replacement tools: candidates (not integrated)

Status: **candidates only. None of these is installed, tested or wired into PAI.** Figures from the GitHub API on 1 Nov 2026. Goal: let the local agent call software and web services that have no official API. Every action that sends, deletes, spends or changes a system still needs the owner's confirm step (PRD APP-12).

| Repo | What it claims to do | License | Stars | Last push |
|---|---|---|---|---|
| [morluto/rea](https://github.com/morluto/rea) | Reverse engineer anything with agents, from app behavior to native binaries | MIT | 416k (verify; unusually high) | 2026-11-01 |
| [kalil0321/reverse-api-engineer](https://github.com/kalil0321/reverse-api-engineer) | Turn a website into a typed API client | MIT | 2.3k | 2026-10-29 |
| [goodnight000/api-anything](https://github.com/goodnight000/api-anything) | Turn a website into an API an agent can call; self-heals when the site changes | MIT | 1.9k | 2026-10-31 |
| [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) | Generate agent-friendly command-line interfaces for existing software | Apache-2.0 | 58k | 2026-09-22 |
| [HelpCode-ai/anythingmcp](https://github.com/HelpCode-ai/anythingmcp) | MCP gateway turning REST, GraphQL, SOAP or SQL APIs into MCP tools | **AGPL-3.0** | 767 | 2026-11-01 |

## Open questions before any of this ships
- Does automating a third-party website or reverse-engineering an app comply with that service's terms? Needs a policy per service; default is official APIs and MCP servers first.
- Safety: unprivileged containers, bound to localhost, no access to the owner's password vault by default.
- AnythingMCP is AGPL-3.0: fine as an unmodified separate service if we offer its source; counsel to confirm.
- Test each on one real workflow before it appears in any product copy.

## Agent runtimes mentioned in planning
Hermes (local reasoning agent) and Rakazo (persistent browser automation) already run in the owner's own fleet. Whether and how they ship on the PAI box is undecided and not designed here.
