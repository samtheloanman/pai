#!/usr/bin/env bash
# PAI VPN Tunnel & Leak Verification Auditor
# Runs on any client (Mac, Linux) to audit mesh connectivity, DNS leakage, and exit node status.

set -euo pipefail

echo "=========================================================="
echo "          PAI MESH VPN CLIENT VERIFICATION AUDIT          "
echo "=========================================================="

echo "[1] Checking Tailscale daemon status..."
if command -v tailscale &> /dev/null; then
    TS_STATUS=$(tailscale status --peers=false)
    echo "  -> Connected as: $TS_STATUS"
elif [[ -x "/Applications/Tailscale.app/Contents/MacOS/Tailscale" ]]; then
    TS_STATUS=$(/Applications/Tailscale.app/Contents/MacOS/Tailscale status --peers=false)
    echo "  -> Connected as: $TS_STATUS"
else
    echo "  [WARN] Tailscale CLI not found in PATH."
fi

echo "[2] Resolving public egress IP..."
PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org || echo "Failed to fetch")
echo "  -> Current Egress IP: $PUBLIC_IP"

echo "[3] Checking DNS resolver and leak safety..."
RESOLVER=$(scutil --dns 2>/dev/null | grep 'nameserver\[0\]' | head -n 1 | awk '{print $3}' || cat /etc/resolv.conf | grep nameserver | head -n 1 | awk '{print $2}')
echo "  -> Active DNS Server: $RESOLVER"

echo "[4] Testing ping to PAI Vault / Dell Host (100.104.238.110)..."
if ping -c 2 -W 2 100.104.238.110 &> /dev/null; then
    echo "  -> [SUCCESS] PAI Gateway (100.104.238.110) is reachable over encrypted WireGuard mesh."
else
    echo "  -> [WARN] PAI Gateway unreachable or ICMP blocked."
fi

echo "=========================================================="
echo "  Audit Complete."
echo "=========================================================="
