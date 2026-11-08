# PAI Network Security Auditor & Engineer (LAN Guardian)

**Objective:** Transform the PAI appliance into an autonomous on-box network security engineer and LAN auditor for home and office environments.

---

## 1. Core Architecture & Open-Source Security Toolchain

```
                                  ┌──────────────────────────────┐
                                  │   PAI Security Agent Core    │
                                  │   (Hermes + LLM Reasoner)    │
                                  └──────────────┬───────────────┘
                                                 │
         ┌───────────────────────────────┬───────┴───────────────────────┬───────────────────────────────┐
         ▼                               ▼                               ▼                               ▼
┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐             ┌─────────────────┐
│ Host Hardening  │             │ LAN Discovery & │             │ Passive Traffic │             │ Zero-Trust &    │
│   & Auditing    │             │ Vulnerability   │             │   Inspection    │             │ Access Control  │
├─────────────────┤             ├─────────────────┤             ├─────────────────┤             ├─────────────────┤
│ • Lynis         │             │ • Nmap (scans)  │             │ • Zeek (meta)   │             │ • Tailscale /   │
│ • nftables      │             │ • RustScan      │             │ • Suricata (IDS)│             │   Headscale     │
│ • Wazuh Agent   │             │ • OpenVAS / CVE │             │ • Pi-hole /     │             │ • eBPF /        │
│   (FIM/Logs)    │             │   correlator    │             │   Unbound DNS   │             │   Cilium filters│
└─────────────────┘             └─────────────────┘             └─────────────────┘             └─────────────────┘
```

---

## 2. The Four Functional Security Layers

### Layer 1: Host Hardening & System Integrity
- **`Lynis`**: Automated local configuration auditor. Runs scheduled compliance audits against the appliance OS (CIS benchmark checks, permission anomalies, unnecessary kernel modules).
- **`Wazuh` (Agent mode)**: Endpoint security, File Integrity Monitoring (FIM) for `/etc` and `/var` configuration drifts, and local auditd log anomaly detection.
- **`nftables`**: Strict kernel-level default-drop packet filtering. Services bind only to localhost (`127.0.0.1`) and the encrypted overlay interface (`tailscale0`).

### Layer 2: Automated LAN Auditing & Device Fingerprinting
- **`Nmap` & `RustScan`**: Periodic non-intrusive subnet discovery scans. Identifies:
  - Rogue devices joining the Wi-Fi/LAN.
  - Unexpected open ports on IoT devices (printers, cameras, smart TVs).
  - Unencrypted protocols (Telnet, HTTP admin portals, exposed UPnP).
- **Vulnerability Correlator**: PAI queries its local offline SQLite CVE database to cross-reference detected software banners against published vulnerabilities, reporting actionable summaries in plain English.

### Layer 3: Passive Traffic Inspection & DNS Guard
- **`Zeek`**: Extracts structured metadata from network packets (DNS queries, TLS certificates, HTTP requests, SSH handshakes) without payload interception.
- **`Suricata` (Passive IDS)**: Evaluates network flows against emerging threat rules to detect malware beacons, cryptominers, or suspicious outbound connections.
- **`Unbound` / `dnscrypt-proxy`**: Encrypted DNS resolver with local DNS-sinkholing (blocking trackers, phishing domains, and ad networks across all household devices).

### Layer 4: Zero-Trust Network Segmentation
- **`Tailscale` / `Headscale` (ZTNA)**: Enforces end-to-end encrypted mesh networking. Devices authenticate through cryptographic keys rather than trusting physical LAN IP ranges.
- **Guest / IoT Isolation**: Uses Linux bridge isolation (`br-guest`) and `ap_isolate=1` (via hostapd) so untrusted smart devices cannot probe the homeowner's primary computers.

---

## 3. How the PAI Agent Acts as a "Network Security Engineer"

1. **Morning Security Briefing**:
   - *"Last night, a new smart plug joined the network at 2:14 AM. It has port 80 and 554 exposed to the LAN. I've placed it in the isolated IoT zone."*
2. **Proactive Hardening Recommendations**:
   - *"Your router still has UPnP enabled. This allows devices to punch holes in your firewall automatically. Here is how to disable it, or I can generate a script."*
3. **Autonomous Incident Response**:
   - If an IoT camera attempts outbound connections to a known malicious IP, Suricata triggers an alert, and PAI updates nftables rules immediately to drop traffic from that MAC/IP address.
