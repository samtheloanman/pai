# AutoResearch: Mesh Networking, Firmware & Off-Grid Stack Evaluation

**Document Version:** 1.0.0  
**Status:** SPECIFICATION & EVALUATION MATRIX  
**Target:** PAI Beam, PAI OS Appliance & UTP Infrastructure

---

## 1. Executive Summary & Verdict Matrix

| Project / Technology | Core Function | Verdict | Role in PAI Ecosystem |
| :--- | :--- | :--- | :--- |
| **1. OpenWrt** | Embedded Linux OS for routers & CPEs | **ADOPT (CORE)** | Foundational OS for PAI Beam routers and CPE nodes. |
| **2. B.A.T.M.A.N. Advanced** | Layer-2 decentralized kernel mesh | **ADOPT (CORE)** | High-speed, zero-config local mesh backhaul (Layer A). |
| **3. Reticulum Network Stack** | Cryptographic zero-infrastructure mesh | **ADOPT (CORE)** | Off-grid, transport-agnostic sovereign data fabric (Layer B). |
| **4. OpenWISP** | Central mass-provisioning & monitoring | **ADOPT (FLEET)** | Fleet firmware manager & automated Zero-Touch Provisioning. |
| **5. LibreMesh** | Multi-radio auto-peering framework | **ADAPT (LAYER)** | Auto-configuration recipes for dual/tri-radio rooftop nodes. |
| **6. Flashable CPEs (MikroTik/Ubiquiti)** | Weatherproof outdoor directional radios | **ADOPT (HARDWARE)** | Production hardware for Tier 2 and Tier 3 PAI Beam links. |
| **7. Meshtastic / MeshCore** | Low-power LoRa hardware & firmware | **ADAPT (EDGE)** | Low-cost ($25) solar emergency beacon & consumer chat. |
| **8. OpenWiFi (TIP)** | Enterprise disaggregated Wi-Fi stack | **CANDIDATE (ENT)** | High-density commercial campus & estate installations. |
| **9. LibreRouter** | Open-hardware multi-radio router | **REFERENCE ONLY** | RF design reference; superseded by modern Wi-Fi 6/7 SoCs. |

---

## 2. In-Depth Project Evaluations

### 1. OpenWrt
* **Verdict:** **ADOPT (CORE MUST-HAVE)**
* **Why It's Important**:
  * Proprietary router firmware (Netgear, ASUS, eero) is a black box that leaks telemetry, limits transmission power, and prevents running custom crypto or container software.
  * OpenWrt is the only open Linux distribution supporting thousands of embedded routers, with full access to `nftables`, `wireguard-tools`, 802.11s mesh, and package management (`opkg`).
* **PAI Integration**:
  * PAI OS builds custom signed OpenWrt images for PAI Beam nodes, embedding PAI's **Network Feed Sentinel**, WireGuard Door 1 keys, and local Unbound DoH resolver.

---

### 2. B.A.T.M.A.N. Advanced (`batman-adv`)
* **Verdict:** **ADOPT (CORE DATA PLANE)**
* **Why It's Important**:
  * Traditional Layer-3 routing (OSPF, BGP, Babel) requires complex subnet planning, IP address management, and dynamic routing daemons.
  * `batman-adv` runs **inside the Linux kernel at Layer 2 (MAC layer)**. It emulates a single, distributed virtual Ethernet switch across shifting multi-hop wireless links.
  * If a neighbor's rooftop node powers off, `batman-adv` automatically finds an alternate wireless path in under 50ms without disconnecting active TCP/UDP connections.
* **PAI Integration**:
  * PAI Beam nodes peer automatically over 5GHz Wi-Fi (802.11s / ad-hoc). Any phone or laptop connecting to any node receives a unified IP lease from the primary PAI gateway via DHCP.

---

### 3. Reticulum Network Stack (RNS)
* **Verdict:** **ADOPT (CORE SOVEREIGN DATA FABRIC)**
* **Why It's Important**:
  * Standard IP networking completely collapses during disasters or ISP blackouts (it requires DNS servers, ARP, ICMP, and global routing tables).
  * Reticulum is an entirely new networking stack designed for **extreme survivability**. Addresses are cryptographic hashes (public keys), not IP addresses.
  * It is **transport-agnostic**: it moves encrypted packets over LoRa, Wi-Fi, Ethernet, serial cable, or the internet interchangeably.
  * Uses **announce-based hop-by-hop routing** (unlike Meshtastic's airtime-choking packet flooding), enabling large-scale multi-hop networks.
* **PAI & UTP Integration**:
  * Reticulum acts as **Layer B (Emergency & Cryptographic Proof Mesh)**.
  * When broadband goes down, PAI OS routes voice memos, critical alerts, and **UTP Bitcoin L2 civic trust proofs** over Reticulum LoRa links spanning 20+ miles.

---

### 4. OpenWISP
* **Verdict:** **ADOPT (ENTERPRISE FLEET CONTROLLER)**
* **Why It's Important**:
  * Managing 50 to 500 individual OpenWrt nodes manually over SSH or LuCI web interfaces is impossible.
  * OpenWISP provides a centralized management server with automated Zero-Touch Provisioning (ZTP), VPN mesh orchestration, telemetry monitoring, and remote firmware flashing.
* **PAI Integration**:
  * Operates as PAI OS's fleet manager. When a user buys a PAI Beam dish and plugs it into their router, it phones home to PAI's local master controller via OpenWISP agent (`openwisp-config`), downloads its cryptographic credentials, and starts meshing automatically.

---

### 5. LibreMesh
* **Verdict:** **ADAPT (CONFIGURATION ENGINE)**
* **Why It's Important**:
  * LibreMesh solved the hardest part of community networks: **automatic channel and radio assignment**.
  * It configures multi-radio hardware out-of-the-box: assigning Radio 1 to 5GHz ad-hoc backhaul, Radio 2 to 2.4GHz client Wi-Fi, and handling local IP prefix allocation.
* **PAI Integration**:
  * Borrow LibreMesh's modular configuration scripts (`lime-packages`) and embed them directly into PAI Beam's base OpenWrt firmware so nodes auto-peer on startup without manual LuCI editing.

---

### 6. Flashable Outdoor CPEs (Ubiquiti LiteBeam, MikroTik SXTsq, TP-Link CPE)
* **Verdict:** **ADOPT (PRIMARY PRODUCTION HARDWARE)**
* **Why It's Important**:
  * Manufacturing custom outdoor RF enclosures with FCC/CE/IC certification costs $250k+ in legal and tooling fees.
  * Ubiquiti, MikroTik, and TP-Link produce millions of carrier-grade, weatherproof (IPX5/IP67) directional antennas and sector dishes priced at **$45 to $95**.
  * They run standard Atheros/MediaTek chipsets that can be flashed with custom OpenWrt firmware.
* **PAI Integration**:
  * PAI Beam Tier 2 and Tier 3 will use pre-flashed, customized **MikroTik SXTsq 5 ac** and **Ubiquiti LiteBeam 5AC Gen2** units as the official plug-and-play outdoor antennas.

---

### 7. Meshtastic & MeshCore
* **Verdict:** **ADAPT (EDGE COMPANION HARDWARE)**
* **Why It's Important**:
  * Uses cheap ($25–$35) ESP32 + Semtech SX1262 LoRa modules (Heltec, LILYGO, RAKwireless).
  * Has a massive existing user base and polished iOS/Android Bluetooth apps.
* **Limitations**:
  * Uses "managed flooding" which causes RF collisions and packet drops in dense metropolitan areas; not suitable as a high-bandwidth backbone.
* **PAI Integration**:
  * PAI OS acts as a **Meshtastic Gateway**: an attached USB LoRa dongle bridges local Meshtastic chat traffic into PAI's Data Lake and relays emergency messages over Reticulum backhauls.

---

### 8. OpenWiFi (Telecom Infra Project - TIP)
* **Verdict:** **CANDIDATE (ENTERPRISE CAMPUS EXPANSION)**
* **Why It's Important**:
  * OpenWiFi disaggregates enterprise hardware from proprietary controllers (Cisco, Meraki, Aruba).
  * Certified white-box access points (Edgecore, CIG, Actiontec) run APNOS (built on OpenWrt) with `uCentral` cloud control.
* **PAI Integration**:
  * Relevant for large commercial mortgage office deployments, multi-acre estates, or municipal Wi-Fi pilots. For residential PAI Beam units, standard OpenWrt + `batman-adv` is lighter and simpler.

---

### 9. LibreRouter
* **Verdict:** **REFERENCE ONLY (DO NOT MANUFACTURE)**
* **Why**:
  * An open-hardware board designed by AlterMundi with 3 radios (two 5GHz + one 2.4GHz) specifically for community mesh.
  * While its multi-radio architecture is brilliant, the hardware design is based on older Atheros AR9558/AR9580 chips (Wi-Fi 4/5).
* **PAI Path**:
  * Emulate LibreRouter’s **antenna and radio-separation topology** using modern MediaTek Filogic (MT7988/MT7986) or Qualcomm Wi-Fi 6/7 platforms rather than fabricating outdated LibreRouter boards.

---

## 3. The Unified PAI Sovereign Mesh Blueprint

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               PAI BEAM COMPLETE ARCHITECTURE                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. HARDWARE FLEET                                                                      │
│ • Master Gateway: PAI OS on Intel N100 / RK3588 (Runs Data Lake + UTP L2 Node)         │
│ • Outdoor Relays: MikroTik SXTsq 5 ac / Ubiquiti LiteBeam 5AC flashed with OpenWrt     │
│ • Off-Grid Emergency: Heltec V3 / RAKwireless LoRa (915 MHz)                           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. BROADBAND MESH DATA PLANE (Layer A)                                                 │
│ • OS: OpenWrt + LibreMesh configuration packages                                       │
│ • Routing Protocol: B.A.T.M.A.N. Advanced (kernel-level Layer 2 virtual switch)        │
│ • Security: OpenSnitch process firewall + PAI Network Sentinel (Rogue AP/DHCP defense) │
│ • Fleet Orchestration: OpenWISP agent for zero-touch cloudless provisioning           │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. CRYPTOGRAPHIC & CIVIC TRUST PLANE (Layer B)                                         │
│ • Protocol: Reticulum Network Stack (Universal encrypted mesh, Ed25519/X25519)         │
│ • Settlement & Governance: UTP Bitcoin Layer 2 (UBTC micro-payments for mesh relay)    │
│ • Truth & Evidence: Graphify Knowledge Graph verifying citations for DAO proposals    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```
