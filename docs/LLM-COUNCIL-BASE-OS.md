# PAI LLM Council: Base Operating System Verdict

**Date:** 2026-11-01  
**Subject:** Selection of the Production Base Operating System for PAI Appliance & PAI OS  
**Compliance Mandates:** PRD §5.1 (OS-1 to OS-9), Zero WAN Ports, Sub-30-Minute First Boot, Unbrickable A/B Rollback, Strix Halo & Ryzen 8000 Hardware Support.

---

## 1. The Expert Council Panel

1. **The Infrastructure Architect (Systems & Reliability)**
2. **The Hardware & Driver Specialist (AMDGPU / RDNA 3.5 / Wi-Fi 6E)**
3. **The Embedded & Appliance Security Engineer (Zero-Trust / Attack Surface)**
4. **The Product & Release Engineer (OTA Updates, DX, Factory Reset)**

---

## 2. Council Deliberations by Candidate

### Candidate A: Arch Linux / Omarchy
- **Infrastructure Architect:** "Arch is rolling-release. Pacman has no native transactional A/B rollback mechanism. An unassisted pacman upgrade can easily break systemd boot or python runtimes in consumer living rooms. It fails PRD OS-1 and OS-2."
- **Hardware Specialist:** "Arch has bleeding-edge kernels, which makes early testing easy, but kernel regressions land immediately with no automated stability gate. Omarchy is maintained by a single enthusiast community; betting a commercial hardware company on it is an unforced risk."
- **Security Engineer:** "Arch desktop packages include massive GUI attack surfaces (Hyprland, Wayland compositors, audio daemons) that waste VRAM and RAM on a 16 GB box that should be headless."
- **Verdict:** **REJECTED for Production Appliance.** (Acceptable only as an opt-in desktop spin for Developer SKUs).

### Candidate B: NixOS
- **Infrastructure Architect:** "NixOS is declarative and deterministic. Rollbacks via generation selection in GRUB/systemd-boot are proven. However, Nix does not package OCI images natively for updates; evaluating nix flakes on low-power mini PCs consumes large amounts of CPU and RAM during updates."
- **Hardware Specialist:** "Packaging out-of-tree firmware or rapidly moving driver firmware (e.g. bleeding edge ROCm/AMDGPU firmware for Strix Halo gfx1151 or MT7922 Wi-Fi) in Nix expressions is notoriously brittle and lags behind upstream Linux."
- **Release Engineer:** "Debugging Nix derivation build failures on a remote appliance is painful. Non-technical users cannot maintain a nix store."
- **Verdict:** **STRONG RUNNER-UP, but deferred.**

### Candidate C: `bootc` (Fedora CoreOS / CentOS Stream 9 Base) — [THE WINNER]
- **Infrastructure Architect:** "`bootc` represents the modern state-of-the-art for container-native Linux operating systems. The entire OS is built with a standard `Containerfile`. Updates are standard OCI image layers (`bootc switch`). If a boot fails or systemd healthchecks fail within 3 minutes, the ostree bootloader automatically reverts to the previous working deployment. It is mathematically unbrickable."
- **Hardware Specialist:** "Because `bootc` builds on Fedora/CentOS Stream kernel trees, we get battle-tested upstream AMDGPU, Vulkan, and MediaTek MT792x drivers with official firmware binaries. When AMD drops Strix Halo support, it lands in the Fedora kernel cleanly."
- **Security Engineer:** "Read-only `/usr`, immutable root filesystem, mutable `/var` and `/etc` overlays. Zero package manager installed on the running appliance (`rpm-ostree`/`bootc` handle image deployment). Services are managed via standard systemd Quadlets, completely isolated."
- **Release Engineer:** "Factory reset is a single native operation: wipe the state overlay, leaving the pristine base image untouched. CI/CD builds the entire OS using standard GitHub Actions `docker build` / `podman build` pipelines, pushing to GHCR."
- **Verdict:** **UNANIMOUS WINNER.**

---

## 3. The Council's Unanimous Verdict & Architectural Rules

1. **Adopt `bootc` (Fedora / CentOS Stream Base) as the Official PAI OS.**
2. **State & Database Protection (Addressing the Red-Team Finding):**
   - The OS update hook must take a pre-upgrade SQLite snapshot:
     ```bash
     sqlite3 /var/pai/pai.db ".backup '/var/pai/snapshots/pai-v$(bootc status --json | jq -r .status.booted.image).db'"
     ```
   - If `greenboot` health check fails on reboot, the systemd rollback unit restores the corresponding database snapshot.
3. **Headless Consumer Default:**
   - Headless server by default; zero GUI packages installed on the consumer image.
   - PAI App, LiteLLM, Speaches, and llama.cpp run as containerized systemd Quadlets.
4. **Developer SKU Distinction:**
   - For users who want a local monitor/desktop UI, ship a separate `pai-os-desktop` image overlaying Omarchy/Hyprland on the bootc base.
