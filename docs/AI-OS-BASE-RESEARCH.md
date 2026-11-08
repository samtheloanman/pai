# PAI OS: base OS research (1 Nov 2026)

Status: research notes, not a decision. Repo figures are from the GitHub API on 1 Nov 2026; items marked (U) are unconfirmed.

## Recommendation

1. **Base OS: a headless, atomic Linux image.** Two candidates, to be chosen by prototyping on real hardware:
   - **NixOS** with our own flake: every change is a new system generation, rollback from the boot menu.
   - **Fedora bootc** (Bluefin/Bazzite-style OCI images): atomic image, rollback by reboot; Fedora tends to get new AMD kernels and ROCm first (U), which matters for Strix Halo.
2. **Agent-config pattern: copy AgntOS's design, not its code.** The agent may write only one module it owns; each change goes propose → confirm → apply → audit log → undo to the previous generation.
3. **Voice layer: Home Assistant's Wyoming services** (openWakeWord, faster-whisper, TTS) without Home Assistant itself. Fallback: OpenVoiceOS.
4. **Omarchy 4: optional desktop/Dev image only.** Arch rolling updates and a Hyprland desktop do not suit a headless appliance. Omarchy's "AI native" means a built-in cloud coding agent; it has no local-model support in the 4.0 release notes.

## Candidates

| Candidate | License | Stars / contributors | Latest activity | Maintainer | Rollback model | Notes |
|---|---|---|---|---|---|---|
| Omarchy (omacom/omarchy) | MIT | 46.0k / 618 | v4.0.6, 2026-10-19 | 37signals / DHH (funding U) | Snapper snapshots, @factory reset | Desktop; no local LLM built in |
| AgntOS (HasNate618/AgntOS) | GPL-3.0 | 0 / 1 | last push 2026-05-26 | One individual | NixOS generations | Dormant 5 months; use the pattern only |
| JarvisOS (JarvisOSLinux) | GPL-3.0 / AGPL-3.0 (repos differ) | 17 / 6 | push 2026-10-31 | Small team | none stated | Research prototype, known security gaps |
| OpenVoiceOS (ovos-installer) | no license file detected (ovos-core: Apache-2.0) | 330 / 31 | v11.0.0, 2026-08-29 | Community | none | Voice assistant framework |
| Home Assistant OS + Wyoming | Apache-2.0 / MIT | 7.6k / 163 (Wyoming 413) | HAOS 18.4, 2026-10-27 | Open Home Foundation | A/B images (U) | Wyoming is the useful part |
| Olares (beclab/Olares) | AGPL-3.0 | 5.3k / 37 | 1.12.7, 2026-09-24 | Beclab (company) | Kubernetes | Too heavy for one box |
| Bluefin / Bazzite (ublue-os) | Apache-2.0 | 2.6k / 158 (Bazzite 9.3k) | weekly stable tags | Community on Fedora bootc | Image rollback | Desktop-oriented |
| Ubuntu Core | mostly GPL (U) | n/a | active | Canonical | Transactional snaps | Snap confinement vs GPU access (U) |
| Plain NixOS flake | MIT (nixpkgs) | very large (U) | very active (U) | NixOS Foundation | Generations | ROCm on Strix Halo may lag (U) |

## Licensing note

GPL and AGPL are acceptable to the owner. Shipping unmodified GPL/AGPL programs as separate services still requires offering their source. Counsel should confirm before launch.

## Open questions

- NixOS vs bootc: decide after a test on real Strix Halo and Ryzen 8745HS hardware (kernel, ROCm/Vulkan).
- A maintained Wyoming wrapper for Kokoro text-to-speech (U).
- Omarchy funding and long-term plan (U).
