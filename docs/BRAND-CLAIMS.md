# PAI brand kit (v0.1, 2026-10-31)

Sources: internal product plan and Oct 2026 market research. Nothing in this file is a medical claim.

---

## 1. Positioning

### The enemy
Surveillance AI: assistants whose business depends on collecting what you say, keeping it on someone else's servers, and deciding later what to do with it. The enemy is not "the cloud" in general. We use the internet for updates, Telegram and email when the owner chooses them, and we say so. What we refuse is an AI that has to watch you to work.

### One sentence
PAI is a small server that runs AI in your home, so your assistant works for you instead of watching you.

### One paragraph
Most AI assistants live on a company's computers and learn from everything you tell them. PAI is a Mac-mini-sized box that runs open-weight AI models on your own hardware. It interviews you on first boot so it actually knows you, keeps that memory on the box, connects to your calendar, email and files, and answers you in the PAI app, Signal, Matrix, Telegram or email. The models run in your house. If you pick a channel run by someone else, we tell you plainly that they carry the message. No PAI account holds your data, telemetry is off by default, and the code is open source.

### 30-second pitch (about 75 words, spoken)
"Every AI assistant you use today runs on someone else's computer and remembers everything you tell it. PAI flips that. It's a small box that sits on your shelf and runs the AI itself. On day one it interviews you, so it knows how you work. Then you message it from your phone, from Signal or Telegram, and it answers using your calendar, your email, your files. The thinking happens at home. It's yours."

---

## 2. Name treatment

- Written: **PAI**, all caps, no periods, never "Pai", "P.A.I." or "pAI".
- Said: "pie". Put the pronunciation on the Kickstarter page once, early: *PAI (say "pie")*.
- What it stands for: Private AI. Use the expansion once per page at most; the name should stand alone.
- Product names: PAI Core, PAI Core 64, PAI Pro, PAI OS, PAI Dev. Always "PAI" plus a capitalised word, no hyphens.
- Never pun on "pie" in headlines (no "a slice of", "easy as"). One light use in social copy is fine.

### Tagline options
1. **Your AI. Your house.**
2. An assistant that doesn't watch you.
3. Your data stays home.
4. Private AI that lives on your shelf.
5. Helpful, not watching.

### Pick: "Your AI. Your house."
Four words, says ownership and location, and it is literally true: inference runs on the box. It names what the owner gets rather than what we are against, which keeps it from sounding like fear marketing. It also avoids an absolute privacy promise: "Your data stays home" (the current Kickstarter title) is false for anyone who turns on Telegram, Gmail, WhatsApp or iMessage, and PLAN.md itself says those providers still carry the message. Use "Your data stays home" only in a sentence that carries the qualifier ("models and memory stay home"). Option 2 is the backup for ad copy where the enemy needs naming.

---

## 3. Voice

PAI talks like a careful engineer explaining her own project to a neighbour: plain words, real numbers, honest limits.

**Rule 1. Say the number, not the adjective.**
- Do: "Runs Qwen3-30B-A3B at 15-30 tokens per second on the Core."
- Don't: "Blazing-fast AI performance."

**Rule 2. Name the limit in the same breath as the feature.**
- Do: "Works with Telegram. Telegram relays bot chats on its servers, so use Signal or the PAI app for anything sensitive."
- Don't: "Chat privately from any app."

**Rule 3. Talk about ownership, not fear.**
- Do: "Your memory file lives on the box. You can read it, edit it, or delete it."
- Don't: "Big Tech is spying on your every move."

**Rule 4. Short sentences, everyday words.**
- Do: "Plug it in. It asks you questions for about 15 minutes. Then it knows you."
- Don't: "Leveraging an AI-native onboarding paradigm, PAI seamlessly builds a holistic user profile."

**Rule 5. Promise only what ships, and say when.**
- Do: "Signal and Matrix: launch or month 1. SIP voice: month 2-3."
- Don't: "Talk to PAI on every platform you love."

**Rule 6. The owner is in charge; PAI is a tool.**
- Do: "PAI writes a page called 'what I will and won't do'. You edit it."
- Don't: "PAI knows what's best for you."

### Banned words and phrases
revolutionary, game-changing, game-changer, cutting-edge, next-gen, next-generation, groundbreaking, disruptive, seamless/seamlessly, effortless, magical/magic, unleash, supercharge, turbocharge, blazing/blazing-fast, lightning-fast, best-in-class, world-class, military-grade, bank-level, unhackable, 100% private, completely private, fully secure, zero risk, AI-powered (as filler), leverage, synergy, empower, paradigm, holistic, robust, state-of-the-art, the future of, ultimate, limitless, runs any model, works with every app, HIPAA compliant, medical-grade, health insights, quiet (until measured; see claims register).

---

## 4. Visual direction

Write-once spec for a designer or an image model. The feeling: a well-made tool on a lived-in desk. Warm, honest, a little nerdy. Not sci-fi, not neon, no glowing brains.

### Palette
| Role | Name | Hex | Use |
|---|---|---|---|
| Primary dark | Walnut | `#2B2420` | Headlines, logo on light, dark backgrounds |
| Background light | Paper | `#F6F1E9` | Page and slide background |
| Accent | Ember | `#D9622B` | One call to action per view, logo dot, key numbers |
| Secondary | Moss | `#4F6B4A` | "Ships at launch" badges, positive states, tier A channel |
| Neutral | Stone | `#8C857C` | Captions, secondary text, rules, borders |
| Warning | Amber | `#C9962E` | "Optional / unsupported" badges, tier C channels |
| Surface | Linen | `#E8E0D3` | Cards, table stripes |

Rules: Ember covers no more than about 10% of any layout. Text is Walnut on Paper or Paper on Walnut (both pass WCAG AA). Never put Ember text on Moss or Amber. No gradients, no glow effects, no purple/blue "AI" palettes.

### Type pair (both free, Google Fonts, OFL)
- **Headlines:** Fraunces, weight 600, optical size high, tight tracking (-1%). Gives warmth and a human hand.
- **Body, UI, specs:** IBM Plex Sans, 400 and 600. **Numbers and code:** IBM Plex Mono 500 (token speeds, prices, commands).
- Sizes for the Kickstarter page images: H1 56-64 px, H2 32-40 px, body 18-20 px, line height 1.5. Sentence case for headings.

### Photo style
- Real PAI hardware only. Kickstarter requires a working prototype and no renders-only page (PLAN.md 1.7, launch checklist). No 3D renders, no AI-generated product images, no composites that change the hardware.
- Setting: real desks and shelves in a real home. Bookshelves, a router, a houseplant, a mug, cables visible but tidy. Wood and fabric, not glass and chrome.
- Light: daylight from a window, soft, warm white balance (about 4500-5200 K). No coloured gels, no RGB light strips.
- Framing: box at human scale next to familiar objects (a paperback, a coffee mug) so size reads. One hero shot at three-quarter view, one top-down on a desk with a phone showing the PAI app, one on a shelf next to a router.
- Screens in shots show real app output from the prototype, captured, not mocked. Blur or replace any personal data on screen.
- People: hands and over-the-shoulder shots of adults. No school logos, house numbers, street views or windows showing the neighbourhood.
- Image-model prompt stub (for mood boards only, never for product shots): "documentary photo, small black mini PC on a wooden home desk, window daylight, houseplant and paperback nearby, warm neutral tones, 35mm, shallow depth of field, no people, no glowing lights".

### Icon style
- Line icons, 2 px stroke on a 24 px grid, rounded caps and joins, no fills except a single Ember dot for emphasis.
- Use Lucide (ISC licence, free) as the base set so icons match the PWA. Custom icons follow the same grid.
- Core set: house (local), lock (tailnet), message bubble (channels), shield-check (A/B rollback), file (local files), calendar, mic (SIP voice, marked "month 2-3"), chip (models).
- Channel badges use the palette, not brand logos: Moss = Tier A (PAI app, Signal, Matrix), Stone = Tier B (Telegram, email), Amber = Tier C optional (WhatsApp, iMessage). Where third-party logos appear, follow each owner's trademark rules and never imply endorsement.

---

## 5. Claims register

Every public claim must appear in the "may make" table, worded no stronger than shown. Source key: **P** = PLAN.md section; **R** = research report section, with the evidence line paraphrased or quoted.

### Claims we may make

| # | Claim (max strength) | Source / evidence line | Notes |
|---|---|---|---|
| 1 | AI models run on the PAI box in your home, not on our servers. | P 1.1, 1.5 (llama.cpp on device). R "Stack": "local inference keeps the model and documents on the box." | Core promise. |
| 2 | There is no PAI cloud and no PAI account that holds your data. Telemetry is off by default. | P Part 2 "What PAI is not", FAQ. | Must be true in shipped code; QA must verify telemetry default. |
| 3 | Your personal memory is stored in a local SQLite file on the box. | P 1.5 Memory. R "Stack": "a single encrypted SQLite file with sqlite-vec... no cloud egress by default is the lowest-operations design." | Say "encrypted" only if the shipped build encrypts it. |
| 4 | First-boot "grill me" interview, about 15 minutes, writes an editable "what I will and won't do" page. | P 1.5 "Grill me" onboarding. | Feature claim; must be in the demo video. |
| 5 | PAI Core runs 20-30B-class models (Qwen3-30B-A3B, gpt-oss-20b) at about 15-30 tokens/s. | P 1.3, Part 2 Specs. R "Strix Halo wins": MoE models are the fast path because bandwidth limits dense models. | The 8845HS speed figure is a PLAN target, not in the report. Re-measure on the prototype before publishing; quote measured numbers. |
| 6 | PAI Pro runs ~120B mixture-of-experts models (gpt-oss-120b, Qwen3.5-122B-A10B) at about 35-55 tokens/s. | R "Strix Halo wins": "gpt-oss-120b at about 53 t/s"; community runs "31-55 t/s depending on backend and context". P 1.3. | Say "about" and "depends on context length". |
| 7 | Dense 70B models run slowly on Pro (about 5 tokens/s) and not on Core. | R: "Llama 3.1 70B dense manages about 5 t/s". P FAQ. | Use as an honesty line, not a feature. |
| 8 | Trillion-parameter frontier models do not run on PAI or any home box. | P "What PAI is not". | Honesty line. |
| 9 | Updates are signed A/B images with automatic rollback; a failed update rolls back instead of leaving the box unbootable. | P 1.5 OS/Updates. R "Ship an immutable, headless OS": Mender-style "A/B partitions with automatic rollback." | Say "designed to roll back automatically". Do not say "can never break". OS choice not final (P 1.5). |
| 10 | PAI listens only on your private network (localhost + Tailscale); no ports are opened to the internet. | P 1.5 gateway. R "Stack": 40,214 exposed OpenClaw instances "traced to listening on all interfaces by default"; appliance "must bind to loopback, expose nothing inbound". | Strong differentiator; cite the 40k figure as "found in Feb 2026 by SecurityScorecard". |
| 11 | Talk to PAI in the PAI app over Tailscale and Telegram at launch; Signal and Matrix at launch or month 1; email at launch; SIP voice month 2-3. | P 1.5 Channels table, 1.6 roadmap. | Dates follow PLAN; stretch goals may move Signal/Matrix and SIP to launch. |
| 12 | Telegram relays bot chats through its servers and is not end-to-end encrypted. | R channels table: Telegram "Cloud chats (not private)". P 1.5: "Medium — Telegram relays bot chats, not E2E". | Must appear wherever Telegram is listed. |
| 13 | "Inference is local. If you choose WhatsApp or iMessage, Meta or Apple still carry the message." | P 1.5 (required campaign copy). R "Chat access": "every message still transits the chat provider." | Mandatory line, verbatim. |
| 14 | It works offline on your home network; the internet is needed only for updates and channels you enable. | P FAQ. | |
| 15 | Bring your own x86 box with the $59 PAI OS image. | P 1.3, reward tiers. | |
| 16 | Everything we ship is open source (MIT/Apache) and public from day one. | P Part 2 "What PAI is", Risks. | Confirm licences of bundled third-party components (R "Recommended plan" step four: Hermes/OpenClaw licences disputed). |
| 17 | Hardware uses off-the-shelf barebones with existing FCC/CE certification; no custom radios. | P 1.6 M0, Risks. R "Hardware margin": radios "need certification with an FCC ID". | Only true once supplier and FCC ID are confirmed. |
| 18 | Nobody else sells a finished, supported, chat-first private AI box in this price band. | R "The market is thin": "Neither is a finished, supported, chat-accessed assistant, which is the open position." P 1.2. | Phrase as "we could not find one" in page copy, and do not name competitors negatively. |
| 19 | Memory (DRAM) prices roughly doubled in 2026, which is why Core starts at 32 GB and Pro costs $3,499. | R "The $1-2k target": TrendForce forecast "Q1 2026 conventional DRAM contract prices up 90-95%"; Framework, Bosgame, Corsair price rises. P 1.2. | Good for the Risks section and pricing FAQ. |
| 20 | Prices: $899 early bird / $999 Core 32 GB, $1,299 Core 64 GB, $3,499 Pro, $3,799 Dev, $59 PAI OS. Delivery targets Jun 2027 (Core), Aug 2027 (Pro), Mar 2027 (software). | P 1.3, reward tiers, timeline. | Targets, not guarantees; Risks section must say so. |
| 21 | Specs per the Part 2 table: Core ~1 L, 65 W; Pro ~4.5 L, 140 W; Core 1 TB, Pro 2 TB NVMe. | P Part 2 Specs. | Size and wattage are PLAN figures; R "Strix Halo wins" says power and noise "were not found in sourced form". Measure on the prototype before publishing. |

### Claims we may NOT make

| Claim | Why not | Source |
|---|---|---|
| Any medical or health claim: manages, tracks, reads, stores or advises on glucose, insulin, diabetes or any condition; "helps people with diabetes"; "health assistant". | PAI is not a medical device or a diabetes product. | P "What PAI is not", 1.7, hard rules. |
| "Works with WhatsApp" / "Works with iMessage" as headline or feature-list items, or any guarantee they work. | Meta's clause bars general-purpose AI bots from Jan 15, 2026; unofficial libraries risk bans; iMessage needs an owner-supplied Mac. Only "optional, owner-installed, unsupported, documented". | R channels table and WhatsApp paragraph. P 1.5, hard rules. |
| "Runs any model", "runs every open model", "frontier performance", "ChatGPT at home". | Core cannot run dense 70B; nothing home-sized runs trillion-parameter models. | R "Strix Halo wins". P "What PAI is not". |
| "100% private", "completely private", "nothing ever leaves your house" without a qualifier. | Telegram, email, WhatsApp and iMessage are carried by third parties. Use "models and memory stay home". | P 1.5, R "Chat access". |
| "Your data stays home" as an unqualified headline. | Same reason. Current Kickstarter title must be qualified or changed (see contradictions). | P 1.5. |
| HIPAA, GLBA or any compliance claim; "safe for patient/client data". | Report says make no HIPAA or GLBA claim; consumer messaging has no BAA. | R "Hardware margin" and "Chat access". |
| "Unhackable", "military-grade", "bank-level" security. | Unprovable; no published threat model yet. | R (WICI critique: "no published threat model"). |
| "Quiet", "silent", specific dB or measured wattage. | Not measured. | R "Strix Halo wins": power and noise "were not found in sourced form, so a 'quiet, always-on' claim cannot yet be made." |
| NPU acceleration as a feature. | Report: "do not sell the NPU". | R "Strix Halo wins". |
| Google Voice support. | No official API. | P 1.5 ("Not promised"). |
| Model licence claims ("all Apache 2.0") before each card is checked. | gpt-oss licence conflicts across sources. | P 1.5, R "Stack". |
| Supplier, DRAM or ship-date certainty ("guaranteed June delivery"). | No supplier quotes yet; DRAM volatile. | P 1.7, R "Recommended plan". |
