#!/usr/bin/env bash
# PAI Mesh VPN Gateway Setup Script
# Configures Linux Host (PAI Appliance or Dell Precision) as an encrypted WireGuard exit node & subnet router.

set -euo pipefail

echo "=========================================================="
echo "         PAI MESH VPN GATEWAY AUTOMATED PROVISIONER       "
echo "=========================================================="

if [[ $EUID -ne 0 ]]; then
   echo "[ERROR] This script must be run as root (sudo)." 
   exit 1
fi

SUBNET_ROUTE="${1:-192.168.50.0/24}"
WAN_IFACE=$(ip route get 8.8.8.8 | awk -- '{print $5; exit}')

echo "[1/4] Configuring Linux Kernel IP Forwarding & BBR..."
cat << 'EOF' > /etc/sysctl.d/99-pai-vpn.conf
net.ipv4.ip_forward = 1
net.ipv6.conf.all.forwarding = 1
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv6.conf.all.accept_redirects = 0
net.ipv4.tcp_syncookies = 1
EOF

sysctl -p /etc/sysctl.d/99-pai-vpn.conf > /dev/null
echo "  -> Kernel sysctl parameters applied successfully."

echo "[2/4] Verifying Tailscale installation..."
if ! command -v tailscale &> /dev/null; then
    echo "  -> Tailscale not detected. Installing via official script..."
    curl -fsSL https://tailscale.com/install.sh | sh
fi

echo "[3/4] Advertising Tailscale Exit Node & Subnet Route ($SUBNET_ROUTE)..."
tailscale up --advertise-exit-node --advertise-routes="$SUBNET_ROUTE" --accept-dns=false --ssh

echo "[4/4] Configuring iptables/nftables MASQUERADE on $WAN_IFACE..."
if command -v iptables &> /dev/null; then
    iptables -t nat -C POSTROUTING -o "$WAN_IFACE" -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -o "$WAN_IFACE" -j MASQUERADE
    iptables -C FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i tailscale0 -j ACCEPT
    iptables -C FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -m state --state ESTABLISHED,RELATED -j ACCEPT
    echo "  -> iptables NAT masquerade rules active on $WAN_IFACE."
fi

echo "=========================================================="
echo "  [SUCCESS] PAI Mesh VPN Gateway is ACTIVE."
echo "  Client devices can now select this node as their Exit Node."
echo "=========================================================="
