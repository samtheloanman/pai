# Design System: PAI OS (Personal AI Operating System)

## 1. Visual Theme & Atmosphere
PAI OS is a quiet, local-first personal operating system. Its interface belongs to the world of architectural drafting tables, Dieter Rams industrial design, and high-craft editorial tools — never sci-fi cockpits, crypto dashboards, or glowing "AI" templates.
- **Mode:** Operate (Impeccable) — scanability, earned familiarity, and precision outrank decoration. The interface recedes into the owner's task.
- **Density:** 6 / 10 (Daily App Balanced — structured ledger rows, generous whitespace, zero nested cards).
- **Variance:** 5 / 10 (Asymmetric 3-pane workspace with structural hairlines rather than floating boxes).
- **Motion:** 3 / 10 (Restrained 160ms `cubic-bezier(0.22, 1, 0.36, 1)` state transitions; zero decorative loops or page-load choreography).

## 2. Color Palette & Roles
Light-first architectural stone palette with a single desaturated mineral accent:
- **Alabaster Canvas** (`#F7F6F2`) — Primary application background (`--bg`)
- **Warm Stone Recessed** (`#EFECE6`) — Sidebars, recessed toolbars, code blocks, and inactive pills (`--surface-2`)
- **Paper Surface** (`#FFFFFF`) — Primary work surface and active input fields (`--card`)
- **Obsidian Ink** (`#18181B`) — Primary typography and headings (`--ink`, contrast 16.4:1 on Paper)
- **Graphite Text** (`#52525B`) — Secondary prose, metadata, and descriptions (`--muted`, contrast 7.1:1 on Paper)
- **Structural Hairline** (`#E2DFD7`) — 1px section dividers and table borders (`--line`)
- **Control Boundary** (`#8E8C84`) — Input, button, and form control borders meeting ≥3:1 non-text contrast (`--border-control`)
- **Mineral Slate-Teal** (`#1D5B58`) — Single restrained accent (saturation 52%) for primary actions, active selection, focus rings, and native `accent-color` (`--teal`)
- **Crimson Alert** (`#991B1B`) — Destructive action confirmation and error text (`--danger`)

## 3. Typography Rules
- **Primary Family:** `Geist` (variable 100–900) — carries headings, body, labels, and controls with a tight 1.15–1.2 scale ratio.
- **Monospace:** `ui-monospace, 'SFMono-Regular', Menlo, monospace` — strictly reserved for ports, hashes, model identifiers, and tabular metrics (`font-variant-numeric: tabular-nums`).
- **Headings:** Weight `600`, tracking `-0.02em`, `text-wrap: balance`, no eyebrow/kicker labels above headings.
- **Body:** `15px` (`0.9375rem`), line-height `1.55`, measure constrained to `65ch` for prose.

## 4. Component Stylings
- **Buttons:** Crisp `8px` radius, `1px solid var(--border-control)`, subtle `-1px` active press feedback, zero outer glow. Primary buttons use solid `#1D5B58` with `#FFFFFF` text.
- **Sections & Containers:** Structural `1px solid var(--line)` panes and border-top ledger rows instead of nested cards. Shadows are subtle (`0 1px 2px rgba(24, 24, 27, 0.04)`) and used only on primary workspace sheets.
- **Inputs & Textareas:** Explicit `<label>` associations, `field-sizing: content` with `width: 100%` and `min-block-size: 3lh` / `max-block-size: 10lh`, `:user-invalid` validation styling, and IME-safe `Enter` handling (`isComposing || keyCode === 229`).
- **Browser Surfaces:** Custom `::selection`, `accent-color`, `caret-color`, `scrollbar-color`, and `@media (forced-colors: active)` fallbacks.

## 5. Layout Principles
- **Workspace Shell:** Full-height `100dvh` CSS Grid (`max-width: 1360px`) with a single top navigation bar and structural workspace panes.
- **No Nested Cards:** Sidebars and inspectors use border-top dividers (`.ledger-row`) rather than card-inside-card boxes.
- **Responsive Collapse:** Multi-column workspaces collapse cleanly to a single column below `960px` with zero horizontal scroll and `≥40px` touch targets.

## 6. Anti-Patterns (Strictly Banned)
- No dark neon/cyberpunk backgrounds or glowing status dots.
- No kicker/eyebrow badges above headings.
- No `//` sci-fi title separators, fake version numbers (`v2.4 // BARE-METAL`), or decorative sparkle icons.
- No 3- or 4-column equal icon-card grids inside cards.
- No fake animated equalizer bars when idle.
- No `Inter` font, no pure `#000000`, no emojis.
