# PAI OS — Network Security, Telemetry & Feed Sentinel Specification

**Document Version:** 1.0.0  
**Status:** SPECIFICATION (AutoResearch Synthesis)  
**Target:** PAI OS Appliance & Workstation Core (`pai`, `pai-mvp`, `os/`)

---

## 1. Executive Summary & Objective

PAI OS is an AI-first, sovereign operating system designed to run private open-weight models and voice agents on local hardware without cloud dependence. 

The primary security threat to a desktop or appliance AI is **network-level exfiltration, connection sniffing, and untrusted network feeds** (e.g., rogue Wi-Fi APs, captive portal interception, evil twin networks, ARP spoofing, rogue DHCP servers, and unauthorized outbound telemetry by installed tools).

**Objective:**
Define the architectural integration of top open-source AI OS frameworks (`agiresearch/AIOS`, `openinterpreter/01`) with host-level network telemetry (`OpenSnitch`, `Portmaster`, `Tetragon`) and implement an automated **Network Feed Sentinel** that:
1. Audits and controls all process-level network connections before packets leave the machine.
2. Continuously audits the physical network feed (Wi-Fi and LAN) at connection time.
3. Automatically triggers an immediate **Fail-Closed Disconnect (Killswitch)** if malicious conditions, rogue gateways, captive redirections, or ARP/DHCP anomalies are detected.

---

## 2. Reusability Analysis: Existing PAI Codebase

| Subsystem / File | Current Capabilities | Reusability for AI OS Network Security | Adaptation Required |
| :--- | :--- | :--- | :--- |
| **`audit.py`** (`audit.db`) | Append-only, tamper-evident SHA-256 hash chain recording user & model actions. | **100% Reusable**. Serves as the central security event ledger for all connection approvals, drops, and feed events. | Add network telemetry event types (`net_connect_blocked`, `rogue_ap_flagged`, `killswitch_engaged`). |
| **`actions.py`** (`pai.db`) | State machine gating risky actions (`none`, `send`, `delete`, `spend`, `system`) with TTL & operator approval. | **100% Reusable**. Acts as the Little Snitch/OpenSnitch confirmation gate for unknown network destinations. | Add executor `network_unblock` and `interface_toggle` under `risk_kind = 'system'`. |
| **`store.py` (v6 Schema)** | `connections_ingress` & `skills_and_tools` tables with "Two Doors, One Rule" privacy tiers (`A`, `B`, `C`). | **100% Reusable**. Schema explicitly models door planes (`door1_mesh`, `door2_blind`, `outbound_opt_in`). | Bind network interface policies (`eth0`, `wlan0`, `tailscale0`) directly to `connections_ingress` tiers. |
| **`routing.py` / `blocks.py`** | 3-tier local router that classifies intents locally before hitting any network interface. | **100% Reusable**. Keeps user interaction 100% local; prevents accidental cloud routing. | Add regex rule blocking prompt injection that attempts outbound webhook or socket exfiltration. |
| **`setup-pai-vpn-gateway.sh`** | Tailscale exit node, nftables MASQUERADE, strict IP forwarding, DNS leak isolation. | **95% Reusable**. Foundational WireGuard overlay for Door 1. | Extend nftables ruleset to support strict fail-closed default-deny on raw physical interfaces. |

---

## 3. Open-Source AI OS & Security Ecosystem Synthesis

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 PAI OS APPLICATION CORE                                │
│   ┌───────────────────────────┐    ┌───────────────────────────┐    ┌──────────────┐   │
│   │    AIOS Kernel Engine     │    │  01 Voice / Local Agent   │    │  PAI Vault   │   │
│   │(Context / Tool Scheduler) │    │  (Open Interpreter Core)  │    │(SQLCipher v6)│   │
│   └─────────────┬─────────────┘    └─────────────┬─────────────┘    └───────┬──────┘   │
└─────────────────┼────────────────────────────────┼──────────────────────────┼──────────┘
                  │                                │                          │
                  ▼                                ▼                          ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        HOST CONNECTION & TELEMETRY LAYER                               │
│  ┌──────────────────────────────────────────────┐  ┌────────────────────────────────┐  │
│  │   OpenSnitch / Tetragon eBPF Kernel Probe    │  │ PAI Action Gate (actions.py)   │  │
│  │   • Process-level outbound socket trap       │  │ • Interactive prompt / confirm │  │
│  │   • Matches UID, Binary Path, Destination IP │  │ • Auto-audited in audit.db     │  │
│  └──────────────────────┬───────────────────────┘  └────────────────┬───────────────┘  │
└─────────────────────────┼───────────────────────────────────────────┼──────────────────┘
                          │                                           │
                          ▼                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                      NETWORK FEED SENTINEL (WIFI & LAN GUARDIAN)                       │
│  ┌─────────────────────────┐  ┌───────────────────────────┐  ┌──────────────────────┐  │
│  │  Rogue AP / Evil Twin   │  │   Rogue DHCP & Gateway    │  │ Captive Portal / MITM│  │
│  │  (apsentry / PMF 802.11)│  │   (dhcpcheck / Static ARP)│  │ (Canary TLS Pinning) │  │
│  └────────────┬────────────┘  └─────────────┬─────────────┘  └──────────┬───────────┘  │
│               │                             │                           │              │
│               └──────────────────────┬──────┴───────────────────────────┘              │
│                                      ▼                                                 │
│                      [ ANOMALY / ROGUE DETECTED? ]                                     │
│                                      │                                                 │
│                     YES ─────────────┴───────────── NO                                 │
│                      │                               │                                 │
│                      ▼                               ▼                                 │
│       ┌──────────────────────────────┐      ┌──────────────────────────────┐           │
│       │    FAIL-CLOSED KILLSWITCH    │      │    DOOR 1 ENCRYPTED TUNNEL   │           │
│       │ • ip link set <dev> down     │      │ • WireGuard / Tailscale Only │           │
│       │ • nftables drop-all on NIC   │      │ • Clean LAN Route Established│           │
│       │ • Log alert to audit.db      │      │ • DNS over HTTPS (DoH) / DNSSEC│          │
│       └──────────────────────────────┘      └──────────────────────────────┘           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Top Open-Source Projects to Leverage
1. **`agiresearch/AIOS`**: Open-source LLM agent operating system. Provides agent-level resource scheduling, context switching, and access control abstraction.
2. **`evilsocket/opensnitch`**: eBPF/Netfilter application firewall. Intercepts outbound connections on Linux per-process and prompts or evaluates granular rules.
3. **`safing/portmaster`**: Privacy-first connection monitor with automatic telemetry blocking, domain lists, and DNS protection.
4. **`cilium/tetragon`**: High-performance eBPF security observability and runtime enforcement. Synchronously terminates processes or closes sockets in kernel space.
5. **`dvlinuxx-max/apsentry`**: Wireless intrusion detection for Rogue APs, Evil Twins, and MAC spoofing.
6. **`elchicodepython/HoneyCheck`** & **`cmatsuoka/dhcpcheck`**: Active and passive rogue DHCP detection.

---

## 4. Subsystem Design: Network Feed Sentinel & Fail-Closed Killswitch

### 4.1 Connection-Time Verification Sequence
Whenever an interface (`eth0`, `wlan0`) transitions to `carrier` or acquires a DHCP lease:
1. **Gate 1: Wi-Fi PMF & BSSID Verification (Wireless only)**
   - Check if the connected AP supports 802.11w Protected Management Frames (PMF).
   - Verify BSSID and OUI against known trusted access points.
   - If identical SSID appears on conflicting channels with unencrypted or downgraded auth -> **FLAG EVIL TWIN**.
2. **Gate 2: Rogue DHCP Audit**
   - Broadcast DHCP Discover probe on the newly attached link.
   - Sniff all `DHCPOFFER` replies for 2.5 seconds.
   - If more than one DHCP server responds, or the offer originates from an unverified IP/MAC -> **FLAG ROGUE DHCP**.
3. **Gate 3: Gateway ARP Pinning & Spoofing Guard**
   - Query gateway IP via ARP.
   - Compare gateway MAC against known subnet gateway cache or permanent neighbor table.
   - If gateway MAC changes without administrative authorization -> **FLAG ARP POISONING / MITM**.
4. **Gate 4: Cryptographic Canary & Captive Portal Prober**
   - Transmit an HTTPS canary probe to `https://canary.pai.internal` or a pinned zero-knowledge endpoint with hardcoded certificate fingerprints.
   - If HTTP 302/307 redirect occurs, DNS returns a non-authoritative IP, or TLS certificate validation fails -> **FLAG CAPTIVE PORTAL / SSL INTERCEPTION**.

### 4.2 Fail-Closed Response Matrix

| Threat Detected | Immediate Hardware Action | Network State | User / Agent Notification |
| :--- | :--- | :--- | :--- |
| **Rogue DHCP Server** | `ip link set dev <iface> down` | Disconnected | Audible warning + Security alert logged in `audit.db`. |
| **Evil Twin / Spoofed AP** | Disconnect Wi-Fi (`iw dev <iface> disconnect`) + blacklist BSSID | Wi-Fi Disabled | Push alert to Mobile App via Door 1 (Tailscale). |
| **ARP Spoofing / Gateway MITM** | Inject kernel drop: `arptables -A INPUT --source-mac ! <MAC> -j DROP` or bring interface down | Hard Isolation | Logged to `audit.db` with attacker MAC address. |
| **Captive Portal / TLS Hijack** | Block all unencrypted egress; restrict traffic strictly to Tailscale/WireGuard UDP 41641 | Mesh Tunnel Only | Prompt user: "Untrusted network feed. Use encrypted overlay only?" |
| **Unauthorized Process Egress** | OpenSnitch/Tetragon blocks socket; triggers `actions.propose(kind='network_unblock')` | Process Isolated | Interactive prompt on PAI UI (:8088). |

---

## 5. Implementation Roadmap & File Locations

1. **`prototype/sentinel/net_feed_guard.py`**:
   - Python daemon implementing Scapy/Socket-based Rogue DHCP listener, ARP validator, and canary TLS prober.
   - Executable by systemd (`pai-net-sentinel.service`).
2. **`prototype/sentinel/rules.nft`**:
   - Fail-closed nftables ruleset enforcing default-deny egress on physical interfaces (`wlan0`, `eth0`), allowing only WireGuard/Tailscale encapsulation (`tailscale0`).
3. **`prototype/app/pai/net_audit.py`**:
   - Integration with `audit.py` to record network feed validation receipts and telemetry stats into `audit.db`.
4. **`os/systemd/pai-net-sentinel.service`**:
   - Systemd unit running as root with `CAP_NET_ADMIN` and `CAP_NET_RAW`.

---

## 6. Acceptance Criteria

- **A1: Rogue DHCP Protection**:
  When a secondary or unauthorized DHCP server answers on the LAN segment, `net_feed_guard.py` flags the violation within 3 seconds and executes `ip link set dev <iface> down`.
- **A2: Gateway Spoof Protection**:
  If an ARP reply claims the gateway IP with an unauthorized MAC, the daemon rejects the packet, locks the permanent neighbor table, and alerts `audit.db`.
- **A3: Captive Portal / MITM Isolation**:
  If an external Wi-Fi network attempts captive portal redirection (HTTP 302 to login page), PAI OS isolates plain HTTP/HTTPS egress and routes exclusively via encrypted Door 1 mesh.
- **A4: Host Egress Gating**:
  Any new executable attempting outbound internet connection is trapped by eBPF/OpenSnitch and requires confirmation via `actions.py` before traffic is released.
- **A5: Tamper-Evident Security Log**:
  Every network feed check, disconnect, and block is permanently hashed into `audit.db`.
