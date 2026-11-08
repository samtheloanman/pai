# PAI Mesh VPN: Secure Zero-Trust Remote & Local Gateway

**Goal:** Turn the PAI host appliance (or Dell Precision / 24/7 node) into a fortified WireGuard Mesh VPN gateway via Tailscale, allowing all client devices (Macs, iPhones, Android phones, laptops) to securely route all external and internal traffic through PAI's encrypted zero-trust umbrella with zero open WAN ports, DNS sinkholing, and cryptographic telemetry defenses.

---

## 1. Network Topology & Trust Boundaries

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             TAILNET ENCRYPTED MESH                               │
│                         (WireGuard Layer 3 Overlay)                              │
│                                                                                  │
│   ┌───────────────────────────┐                ┌─────────────────────────────┐   │
│   │     Mobile iPhone/iOS     │                │     Android / Laptop        │   │
│   │     100.93.199.90         │                │     100.73.237.119          │   │
│   │  (tag:pai-client)         │                │  (tag:pai-client)           │   │
│   └─────────────┬─────────────┘                └──────────────┬──────────────┘   │
│                 │                                             │                  │
│                 │   Encrypted Tunnel (ChaCha20-Poly1305)      │                  │
│                 └───────────────────────┬─────────────────────┘                  │
│                                         ▼                                        │
│                        ┌─────────────────────────────────┐                       │
│                        │       PAI GATEWAY APPLIANCE     │                       │
│                        │       dell-precision            │                       │
│                        │       100.104.238.110           │                       │
│                        │       LAN: 192.168.50.127       │                       │
│                        │       (tag:pai-box)             │                       │
│                        └────────────────┬────────────────┘                       │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │
                  ┌───────────────────────┴───────────────────────┐
                  ▼                                               ▼
   ┌─────────────────────────────┐                 ┌─────────────────────────────┐
   │    Internal Secure LAN      │                 │    Encrypted WAN Egress     │
   │    (192.168.50.0/24)        │                 │    (Clean ISP Exit)         │
   │ • Fast-API Vault (:8000)    │                 │ • DNS via Sinkhole (Unbound)│
   │ • LLM Inference (:11434)    │                 │ • Ad/Telemetry Blocker      │
   │ • Rakazo / Browser VM       │                 │ • No public IP exposure     │
   └─────────────────────────────┘                 └─────────────────────────────┘
```

---

## 2. Gateway Node Configuration (Linux Host / PAI Appliance)

### A. Kernel Hardening & Forwarding (`/etc/sysctl.d/99-pai-vpn.conf`)
Enable packet forwarding, TCP BBR congestion control, and reverse-path filtering to prevent IP spoofing:

```ini
# IPv4 and IPv6 packet forwarding for VPN egress
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1

# TCP BBR + Fair Queuing for low latency audio/video streaming
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Reverse path filtering (Drop spoofed ingress packets)
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1

# Disable ICMP redirect acceptance
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0

# SYN flood protection
net.ipv4.tcp_syncookies = 1
```

Apply immediately:
```bash
sudo sysctl -p /etc/sysctl.d/99-pai-vpn.conf
```

---

### B. Tailscale Gateway Activation

Advertise the host node as an **Exit Node** and route the local subnet:
```bash
sudo tailscale up \
  --advertise-exit-node \
  --advertise-routes=192.168.50.0/24 \
  --accept-dns=false \
  --ssh
```

---

### C. `nftables` Default-Drop & NAT Masquerade (`/etc/nftables.conf`)

Ensure client traffic traversing `tailscale0` is NAT-masqueraded when exiting to the physical LAN/WAN interface (`eth0` or `enp0s31f6`):

```nft
table inet pai_filter {
    chain input {
        type filter hook input priority filter; policy drop;

        # Allow established and related connections
        ct state established,related accept

        # Allow loopback
        iifname "lo" accept

        # Allow all WireGuard mesh traffic on tailscale0
        iifname "tailscale0" accept

        # Allow local subnet SSH & ICMP ping only
        ip saddr 192.168.50.0/24 tcp dport 22 accept
        icmp type echo-request accept
    }

    chain forward {
        type filter hook forward priority filter; policy drop;

        # Allow forwarding from tailscale0 out to WAN/LAN
        iifname "tailscale0" accept
        ct state established,related accept
    }
}

table ip pai_nat {
    chain postrouting {
        type nat hook postrouting priority srcnat; policy accept;

        # Masquerade traffic exiting physical WAN/LAN interface
        oifname != "tailscale0" ip saddr 100.64.0.0/10 masquerade
    }
}
```

Reload firewall:
```bash
sudo nft -f /etc/nftables.conf
```

---

## 3. Client Configuration (iOS, Android, macOS, Windows)

### iOS & Android (PAI Telemetry Sentinel)
1. Open **Tailscale** on the mobile client.
2. Tap the three dots `...` (or Settings) -> **Exit Node**.
3. Select `dell-precision` (or your PAI box).
4. Toggle **Use Exit Node**.
5. Enable **Allow Local Network Access** (to reach local printers/Chromecast if desired, or disable for full zero-trust lockdown).
6. Under Android / iOS VPN Settings:
   - Toggle **Always-on VPN: ON**
   - Toggle **Block connections without VPN (Killswitch): ON**

### macOS Client
Run:
```bash
tailscale set --exit-node=dell-precision --exit-node-allow-lan-access=true
```

To deactivate:
```bash
tailscale set --exit-node=""
```

---

## 4. Leak Verification & Healthcheck

Run the PAI VPN verification script to ensure 100% encryption, zero DNS leakage, and verified gateway IP:

```bash
curl -s https://am.i.mullvad.net/json | jq '{ip: .ip, country: .country_name, blacklisted: .blacklisted}'
```

Verify DNS server address is the PAI sinkhole:
```bash
dig whoami.akamai.net +short
```
