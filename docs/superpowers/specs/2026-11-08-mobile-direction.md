# Mobile direction: Capacitor wrapper vs PocketPal AI shell

Status: **decision pending (Sam)**. Nothing is built yet.

## Options

**(a) Capacitor wrapper around `prototype/web`.** Ship the existing React UI as an iOS/Android app. The phone is a thin client; inference, voice, and the SQLCipher vault stay on the home box, reached over LAN or Tailscale.

**(b) PocketPal AI (MIT, React Native + llama.rn) as the native shell.** Fork an existing on-device chat app and add PAI features. Models run on the phone.

## Comparison

| | (a) Capacitor | (b) PocketPal fork |
|---|---|---|
| Code reuse | Reuses `prototype/web` as is | New RN UI; PAI screens rebuilt |
| Where AI runs | Home box (current architecture) | On the phone (llama.rn) |
| Works offline / away from home | Only with a tunnel (Tailscale) to the box | Yes, with small models |
| Model quality | Whatever the box runs | Limited by phone RAM (~1–4B models) |
| Vault / memory | One vault on the box; no sync problem | Needs a phone-side store + sync with the box |
| Approvals, audit, cloud masking | Already implemented server-side | Must be ported or proxied |
| Effort to first build | Small (days) | Large (weeks), plus upstream merge burden |
| Licence | Ours | MIT, compatible; keep notice |
| Battery / heat | Low | High during inference |

## Recommendation

Start with **(a)**: it matches PAI's "your home box is the brain" design, keeps one vault, and reuses the tested UI. Revisit (b) later only for an offline "pocket mode", likely by adding llama.rn to the Capacitor app or as a separate companion rather than forking PocketPal.

## Open questions for Sam

1. Is offline use away from home a must-have for v1? If yes, (b) or a hybrid.
2. Is Tailscale acceptable as the default remote-access path?
