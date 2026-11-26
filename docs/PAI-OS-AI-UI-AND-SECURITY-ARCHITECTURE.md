# PAI OS — AI-First Linux UI, Multi-Shield Security & Intelligent Diagnostics

**Status:** SPECIFICATION & ARCHITECTURAL BLUEPRINT  
**Target:** PAI OS Appliance, Laptop Client & Portable Node (`pai`, `pai-mvp`)

---

## 1. AI-First UI for Linux: Open-Source Code to Leverage

Instead of building a desktop interface from zero, PAI OS combines the best elements of three leading open-source desktop AI projects:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               PAI OS AI-FIRST DESKTOP UI                               │
├───────────────────────────────┬───────────────────────────────┬────────────────────────┤
│ Layer 1: The Ambient Shell    │ Layer 2: The Agentic Core     │ Layer 3: System HUD    │
│ (Inspired by openinterpreter) │ (Inspired by Jan.ai / JanHQ)  │ (Inspired by Starling) │
├───────────────────────────────┼───────────────────────────────┼────────────────────────┤
│ • Voice-first breathing iris  │ • Local model management      │ • Real-time Trust HUD  │
│ • Floating push-to-talk bar   │ • Hardware acceleration auto- │ • Network health status│
│ • Natural turn-taking audio   │   detection (Vulkan/Metal)    │ • Quick-toggle security│
│ • Zero-clutter minimal canvas │ • Sandboxed file / tool RAG   │ • Process egress alerts│
└───────────────────────────────┴───────────────────────────────┴────────────────────────┘
```

### Top 3 Open-Source Projects to Fork/Borrow From:
1. **`openinterpreter/01-app` & `01`**:
   - **Code to Borrow**: The React Native/Electron voice state machine, real-time WebSocket audio streaming, and ambient conversational visualizer.
   - **Value**: Gives PAI OS its signature *Her*-style ambient presence with sub-400ms voice turn-taking.
2. **`janhq/jan` (Jan AI)**:
   - **Code to Borrow**: The cross-platform Electron/TypeScript architecture, Nitro C++ local engine bindings, and offline-first model downloader.
   - **Value**: Robust, battle-tested UI for model switching (`gemma3:4b`, `llama3.2`, `qwen2.5`) with zero cloud telemetry.
3. **`starling-build/starling` / System76 `COSMIC Desktop`**:
   - **Code to Borrow**: Wayland native applets, global hotkey overlay (Spotlight/Raycast replacement), and notification tray daemons.
   - **Value**: Enables PAI to live as a system-wide companion that can be summoned with a single keystroke anywhere in Linux.

---

## 2. Multi-Shield Security: Tailscale + Cloudflare + Local Open-Source

PAI OS secures all connections across three complementary layers:

```
                  ┌──────────────────────────────────────────────┐
                  │            PAI CLIENT / APPLIANCE            │
                  └──────────────────────┬───────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌───────────────────────┐    ┌───────────────────────┐    ┌───────────────────────┐
│       SHIELD 1:       │    │       SHIELD 2:       │    │       SHIELD 3:       │
│    TAILSCALE MESH     │    │  CLOUDFLARE ZERO-TRUST│    │  LOCAL HOST SENTINEL  │
├───────────────────────┤    ├───────────────────────┤    ├───────────────────────┤
│ • Door 1 WireGuard    │    │ • Cloudflare Tunnel   │    │ • OpenSnitch eBPF     │
│ • Device tags:        │    │   (Zero Open Ports)   │    │   process firewall    │
│   tag:pai-box/client  │    │ • 1.1.1.1 DoH with    │    │ • nftables fail-closed│
│ • MagicDNS resolution │    │   DNSSEC & malware cut│    │ • usbguard BadUSB cut │
│ • Full-tunnel exit    │    │ • Shielded Door 2     │    │ • audit.db SHA-256    │
│   node on untrusted   │    │   webhook ingress     │    │   tamper-evident log  │
└───────────────────────┘    └───────────────────────┘    └───────────────────────┘
```

1. **Tailscale (Door 1 — Sovereign Encrypted Overlay)**:
   - Every PAI node joins an encrypted WireGuard mesh (`100.x.y.z`).
   - Devices authenticate via cryptographic node keys; public internet ports remain closed.
   - When on public Wi-Fi, the client toggles **Full-Tunnel Mode**, routing 100% of traffic through the user's home PAI Box.
2. **Cloudflare Zero Trust (Door 2 — Shielded Ingress/Egress & Encrypted DNS)**:
   - Inbound webhooks (e.g. mobile app notifications, external voice endpoints) run via `cloudflared` tunnels. No port forwarding on the home router.
   - All DNS queries resolve over DNS-over-HTTPS (DoH) via `1.1.1.1` with DNSSEC verification, bypassing local ISP eavesdropping and DNS injection.
3. **Local Host Sentinel (Linux Kernel & Hardware Hardening)**:
   - **OpenSnitch eBPF Daemon**: Traps every outbound network socket per process path and user ID; integrates with PAI’s `actions.py` approval gate.
   - **`nftables` Fail-Closed Ruleset**: Raw physical interfaces (`eth0`, `wlan0`) are blocked from general egress unless validated or routed through `tailscale0`.
   - **`usbguard`**: Automatically locks down USB endpoints against BadUSB keystroke injection.

---

## 3. Clear Intelligent Diagnostics: `pai-net-diag` & Trust Score HUD

Whenever a PAI device connects to a physical Wi-Fi or LAN feed, `pai-net-diag` executes an autonomous **6-Gate Security Audit** in under 3 seconds:

| Gate | Audit Performed | Threat Detected | Diagnostic Result |
| :--- | :--- | :--- | :--- |
| **1. Gateway & ARP** | Queries default gateway IP; compares MAC to permanent neighbor table and OUI database. | ARP spoofing, Man-in-the-Middle (MITM), duplicate IP collisions. | Pass: Known gateway MAC.<br>Fail: Gateway MAC mismatch. |
| **2. DHCP Sentry** | Broadcasts DHCP DISCOVER probe; monitors for multiple or unauthorized DHCPOFFERs. | Rogue DHCP servers pushing malicious default gateways or DNS overrides. | Pass: Single authorized server.<br>Fail: Rogue DHCP IP flagged. |
| **3. DNS Hygiene** | Resolves canary domains across local DHCP DNS vs. Cloudflare DoH (`1.1.1.1`) vs. Quad9 (`9.9.9.9`). | DNS hijacking, NXDOMAIN redirection, censorship, or missing DNSSEC. | Pass: Identical cryptographic IPs.<br>Fail: DNS poisoning detected. |
| **4. TLS Canary** | Probes pinned HTTPS canary endpoint (`https://canary.pai.internal`); verifies root certificate fingerprints. | Captive portal redirection (HTTP 302/307), SSL strip, or MITM proxy certificates. | Pass: Valid pinned fingerprint.<br>Fail: Interception / captive redirect. |
| **5. Egress & VPN** | Tests WireGuard UDP 41641 handshakes and HTTPS 443 egress; checks for plaintext DNS leaks. | ISP port blocking, throttled VPN handshakes, or plaintext leakages. | Pass: Unfiltered WireGuard link.<br>Fail: Tunnel blocked / DNS leak. |
| **6. Airspace Noise** | Sniffs 802.11 management frames via internal Wi-Fi or ESP32 Sentinel; checks PMF status. | Deauthentication floods (type 0, subtype 12), Evil Twin SSIDs, BLE advertisement floods. | Pass: Clean RF spectrum & PMF active.<br>Fail: Deauth storm / BSSID clone. |

---

## 4. The 3-State Visual Trust HUD (Inside the PAI Desktop UI)

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 🟢 SOVEREIGN SECURE (Trust Score: 95/100)                                              │
│ All 6 diagnostic gates green. Trusted home/office LAN. Local direct routing engaged.   │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🟡 UNTRUSTED FEED / SHIELD ACTIVE (Trust Score: 70/100)                                │
│ Public network or captive portal detected. Local raw egress BLOCKED.                   │
│ Automatic Action: Tailscale Full-Tunnel WireGuard engaged. All traffic encrypted.      │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 🔴 COMPROMISED NETWORK / FAIL-CLOSED (Trust Score: 20/100)                             │
│ CRITICAL THREAT: Rogue DHCP or ARP poisoning detected on link!                         │
│ Automatic Action: Physical link dropped (`ip link set down`). Airgap enforced.         │
│ Voice Alert (Ava): "Malicious network feed detected. Disconnected to protect device." │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
