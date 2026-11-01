# PAI networking tiers on Linux: modules, packages, install (research notes)

As of 2026-10-31. Not legal advice. Tags: [V] verified today against a primary source (package repo API, kernel config, GitHub API, upstream file); [S] secondary source or forum, treat as likely; [U] unverified, from memory or inferred, test before relying.

Context: tier 1 = private encrypted overlay between owner's own boxes; tier 2 = opt-in isolated guest Wi-Fi with kill switch and caps; tier 3 = optional community mesh, off by default, separate project. Product plan: `../BUILD-PLAN.md` (headless immutable image for consumer SKUs, Omarchy 4 only on the Dev image, Tailscale for remote access, nothing on public interfaces).

## 0. Findings that change the design

1. The kernel side is a non-issue. Stock Arch (linux 7.2.14.arch1) and Fedora rawhide kernel configs both enable: WIREGUARD=m, MAC80211_MESH=y, BATMAN_ADV=m, NF_TABLES=m, NFT_CT/NAT/LIMIT/CONNLIMIT=m, NET_SCH_CAKE=m, NET_SCH_FQ_CODEL=y, NET_SCH_HTB=m, NET_SCH_INGRESS=m, IFB=m, BRIDGE_NETFILTER=m, IWLWIFI=m, MT7921E/MT7925E/MT7921U/MT76x2U=m, RTW89_8852AE=m [V: `config.x86_64` from gitlab.archlinux.org/archlinux/packaging/packages/linux, and `kernel-x86_64-fedora.config` from src.fedoraproject.org, both fetched 2026-10-31]. Ubuntu not checked [U], but its kernels carry the same options historically.
2. The Wi-Fi card, not the kernel, decides tier 2. Intel AX200/AX210/BE200 effectively cannot host a 5 or 6 GHz AP (channels flagged NO-IR; 2.4 GHz only, slow) [S: morrownr/USB-WiFi discussion 557 (BE200: 2.4 GHz AP ~30-50 Mbps, 5 GHz refused, 6 GHz no-IR); Intel community threads on AX210 6 GHz hotspot and AX200 5 GHz].
3. MediaTek MT7925 worked as a hostapd AP on 2.4 GHz (~90 Mbps) and 5 GHz (~140 Mbps, likely 40 MHz, quick informal test) on Arch, 6 GHz AP channels showed no-IR [S: same discussion]. MT7921 AP mode is upstream since 5.18 [S: Ubuntu launchpad bug 1979173]; 160 MHz AP for MT7922 landed 2025 [S: mt76 git log]. Reports: no 160/80+80 or MLO AP on MT7925 [S: OpenWrt forum BPi-R4 thread]; one 6 GHz hostapd crash report on mt7921 reset path [S: Arch BBS 303518].
4. Do not use Wi-Fi as the PAI uplink while serving guests. The box has Ethernet; a single radio can only do AP+STA on the same channel. Design: Ethernet = WAN, Wi-Fi card = AP only. Concurrent AP+STA is a fallback, not the default. Confirm with `iw list` on the real card [U for exact combos].
5. Omarchy 4.x uses NetworkManager. Latest release v4.0.6 (2026-10-19), repo `omacom/omarchy`, default branch `quattro`; 4.0.5 ships kernel 7.2.8 + BORE [V: GitHub API, newreleases.io]. Base package list contains `networkmanager`, `ufw`, `ufw-docker`, `wireless-regdb`, `bluez*`, and no `iwd`/`impala`; `omarchy-restart-wifi` calls `nmcli` [V: raw files on quattro]. Older Omarchy (1.3) used iwd + Impala [S]; whether iwd is still installed on a given box: check `systemctl is-enabled iwd` [U]. limine/btrfs/snapper not re-verified [U].
6. Omarchy ships `ufw`. Our nftables guest rules must coexist with it (see 3.5).

## 1. Tier 1 overlay options

| Option | Kernel / userspace | Arch (verified 2026-10-31) | Fedora/Ubuntu | License | NAT traversal | Central server | Notes |
|---|---|---|---|---|---|---|---|
| WireGuard raw | in-kernel `wireguard`, `wg` | `wireguard-tools` 1.0.20260223 (extra) [V] | `wireguard-tools` (dnf/apt) [U name, standard] | GPL | none built in; needs reachable endpoint or helper | none | Smallest, but you write key exchange + hole punching yourself |
| Tailscale | `tailscaled` userspace Go over WireGuard (kernel or userspace) | `tailscale` 1.104.4 (extra, MIT per pkg metadata; upstream LICENSE is BSD-3-Clause) [V] | official repo `pkgs.tailscale.com/stable/{fedora,ubuntu}` [U path] | client BSD-3 [V GitHub API]; coordination server proprietary SaaS [S] | best in class: STUN, DERP relays, hole punching [S] | yes, Tailscale SaaS, or headscale | Easiest; sold-product dependency on a third-party SaaS and its ToS: get a written OK / commercial terms [U] |
| Headscale | control server only; clients stay Tailscale | `headscale` 0.29.7 (extra, BSD-3) [V] | binary/deb/rpm from GitHub releases [U] | BSD-3 [V] | uses the Tailscale client | self-hosted by you | Designed for one tailnet [U]; per-customer isolation means one instance per customer or a different design |
| Nebula | `nebula` userspace Go, own CA | `nebula` 1.12.0 (extra, MIT) [V] | `nebula` in Fedora repo [U]; GitHub release deb/rpm | MIT [V] | hole punching via lighthouses | needs lighthouse(s) with public IP, no vendor | Each customer's CA = natural per-owner isolation; PAI could host a free lighthouse or ship a relay option |
| ZeroTier | `zerotier-one` userspace | `zerotier-one` 1.16.2 (extra, MPL-2.0) [V] | vendor repo [U] | MPL-2.0 for most; `nonfree/` dir is source-available [V: upstream LICENSE.txt]; GitHub API reports NOASSERTION [V] | yes, via planet/roots | ZeroTier Inc. roots unless you run your own controller/moon | Licensing is the messiest for a sold product: read `nonfree/LICENSE.md` with counsel |
| Yggdrasil | `yggdrasil` userspace, TUN | `yggdrasil` 0.5.15 (extra, LGPL-3.0-only) [V] | COPR/PPA/GitHub deb [U] | LGPL-3.0 | peers over TCP/TLS/QUIC; multicast LAN discovery | none (public peer list) | Self-described alpha/experimental, no external audit [S: F-Droid/pkg notes]; multicast peering leaks MAC [S]. Better tier 3 than tier 1 |

Resource use [U, expect small]: WireGuard kernel path negligible; tailscaled/nebula/yggdrasil are single Go processes, tens of MB RSS and low single-digit % CPU idle on a Ryzen mini PC. Measure in `pai-bench`.

Recommendation: ship Tailscale (matches BUILD-PLAN) with a documented headscale switch for owners who want no vendor; keep Nebula as the vendor-free alternative if Tailscale terms block bundling. Avoid ZeroTier for licensing reasons. Don't use `--accept-routes`/exit-node defaults on boxes that also serve guests.

## 2. Wi-Fi in the kernel

Stack: `cfg80211` (regulatory + nl80211 API) -> `mac80211` (soft-MAC; `CONFIG_MAC80211_MESH=y` gives 802.11s mesh point on every stock kernel [V]) -> driver (`iwlwifi`, `mt76`, `rtw89`...). Userspace: `iw` 6.17 (core) [V], `hostapd` 2.12 (extra) [V], `wpa_supplicant` 2.12 (core) [V], NetworkManager 1.58.1 [V] (its AP/hotspot mode wraps wpa_supplicant; fine for demos, too weak for isolation/caps: use hostapd). batman-adv: `CONFIG_BATMAN_ADV=m` [V] + `batctl` 2026.3 (extra) [V]; layer-2 mesh over 802.11s or ad-hoc, tier 3 only.

Check on each candidate card:
```
iw list | sed -n '/Supported interface modes/,/Band 1/p'    # need "* AP" and "* mesh point"
iw list | sed -n '/valid interface combinations/,/Device supports/p'
iw reg get ; iw list | grep -E 'NO-IR|DFS|radar|no IR|Disabled'
```
Want a combination line like `{ managed } <= 1, { AP } <= 1, total <= 2, #channels <= 1`. mt76 usually reports one channel for AP+managed [U]; Intel iwlwifi reports AP in combinations but NO-IR/LAR blocks 5/6 GHz AP in practice [S].

| Chipset (typical module) | AP 2.4 | AP 5 | AP 6 | 802.11s | Verdict |
|---|---|---|---|---|---|
| Intel AX200/AX210 | yes | blocked by NO-IR/LAR on many setups [S]; `lar_disable=1` workaround unconfirmed [U] | no (no-IR) [S] | not supported by iwlwifi firmware [U] | Fine as client, poor as AP |
| Intel BE200 | yes, slow [S] | refused [S] | no-IR [S] | [U] | Same |
| MediaTek MT7921 (RZ608) / MT7922 (RZ616) | yes | yes (AP since 5.18) [S] | AP not usable in practice [S][U] | mt76 supports mesh point [U] | Best proven. 160 MHz AP for MT7922 since 2025 [S] |
| MediaTek MT7925 (RZ717, Wi-Fi 7) | yes ~90 Mbps [S] | yes ~140 Mbps [S] | no-IR [S] | [U] | Works as 11ax AP; no MLO/EHT-AP, no 160 [S]; morrownr says Wi-Fi 7 AP needs ~a year to settle [S] |
| Realtek RTL8852 (rtw89) | [U] | [U] | [U] | [U] | Not verified; avoid for AP |
| Qualcomm (ath11k/ath12k, WCN685x, QCNFA765) | AP supported in driver [U] | [U] | [U] | [U] | Rare in mini PCs; AP works in OpenWrt-class use; firmware blob quality varies [U] |

Recommendation: MediaTek MT7922 (Wi-Fi 6E, RZ616) or MT7925 (RZ717) in the M.2 2230 slot. For the AP SKU prefer MT7922 for maturity unless a Wi-Fi 7 client is a selling point, in which case MT7925 with AP kept at 11ax, 5 GHz ch 36-48/149-165 (non-DFS), 80 MHz. AP-only on Ethernet WAN. Strix Halo boxes: card varies by OEM (often MediaTek MT7925 or Intel BE/AX) [U]: make "MT792x only, no Intel" a BOM requirement and check `lspci -nn | grep -i network` on the sample.

Fallback (USB, in-kernel, no DKMS): MT7921AU adapters (Comfast CF-953AX, Alfa AXML; needs kernel >= 5.19 for AP) and MT7612U (Alfa AWUS036ACM; in-kernel since 4.19, no DFS channels in 5 GHz AP, may need `mt76_usb disable_usb_sg=1`) [S: morrownr/USB-WiFi, morrownr/7612u]. Avoid Realtek Wi-Fi 6/7 USB.

## 3. Guest network design

3.1 Topology: Ethernet `eth0` = WAN; `wlan-ap` (hostapd) joined to bridge `br-guest` 10.77.0.1/24 (own subnet, no VLAN needed with one radio; add `bridge vlan` only if wired guest ports are added). dnsmasq on `br-guest` only (`interface=br-guest`, `bind-interfaces`) does DHCP + DNS. Optional: forward DNS to local `unbound` with a blocklist (Pi-hole style) on 10.77.0.1:5353.
3.2 hostapd: `ap_isolate=1` (stops guest-to-guest), `country_code=US`, `ieee80211d=1`, `ieee80211h=1` (needed for DFS), `wpa_key_mgmt=SAE WPA-PSK` with `ieee80211w=1` (transition), `max_num_sta=16`, `bridge=br-guest`, ch 36 or 149, `ieee80211ax=1`, `he_su_beamformer=0` if flaky. Note morrownr saw `bridge=` break forwarding in one test on BE200/MT7925 [S]: create the bridge first with networkd and verify.
3.3 nftables (the single source of truth; file `/etc/nftables.d/pai-guest.nft`):
```
table inet pai_guest {
  set blocked4 { type ipv4_addr; flags interval; elements = { 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, 169.254.0.0/16, 127.0.0.0/8 } }
  chain input   { type filter hook input priority -10; policy accept;
     iifname "br-guest" udp dport {53,67} accept
     iifname "br-guest" tcp dport 53 accept
     iifname "br-guest" ct state established,related accept
     iifname "br-guest" drop }                       # blocks PAI API, SSH, everything else on the host
  chain forward { type filter hook forward priority -10; policy accept;
     iifname "br-guest" oifname != "eth0" drop
     iifname "br-guest" ip daddr @blocked4 ip daddr != 10.77.0.1 drop
     iifname "br-guest" ip6 daddr != ::/0 drop }     # v6 off for guests v1
  chain post    { type nat hook postrouting priority 100; oifname "eth0" ip saddr 10.77.0.0/24 masquerade }
}
```
Plus: PAI API must bind 127.0.0.1 or the LAN/tailnet interface only, never 0.0.0.0 [policy], and the input drop above is the second wall. The guest block of 192.168/16 etc. also protects the owner's home LAN behind the same router [V logic, rules [U] until tested].
3.4 Rate limits: (a) fairness + cap with CAKE: `tc qdisc replace dev eth0 root cake bandwidth 20mbit besteffort nat dual-srchost` (upload) and an `ifb0` ingress shaper `cake bandwidth 50mbit dual-dsthost` for download, applied to guest traffic only by marking in nftables (`meta mark set 0x77`) and `tc filter ... fw`, or simpler v1: shape `br-guest` egress (guest download) with cake `dual-dsthost` and `ifb` for guest upload [U exact syntax, `sch_cake`/`ifb` are in stock kernels, V]. (b) per-client hard cap via nft dynamic set: `add @guestflows { ip saddr limit rate over 2 mbytes/second } drop` in the forward chain [U]. Owner caps (GB/day, Mbps) are written to `/etc/pai/guest.toml` and rendered into these files.
3.5 Kill switch (owner button/API): `systemctl stop pai-guest.target` (stops hostapd@wlan-ap, dnsmasq-guest, flushes `table inet pai_guest`, `iw dev wlan-ap set power_save off`, `rfkill block` not used since it would kill the client radio). Hard stop also `ip link set wlan-ap down`. State flag `/var/lib/pai/guest.enabled` default absent = off; unit has `ConditionPathExists`. Auto-off timer and traffic quota via `pai-guest-quota.timer` reading `nft list counter`.
3.6 ufw on Omarchy: ufw is in the base image [V]; its iptables-nft chains can still drop forwarded packets even if our table accepts (any base-chain drop wins) [U]. Either `ufw route allow in on br-guest out on eth0` + `ufw allow in on br-guest to any port 53,67 proto udp`, or leave ufw alone and put the rules in ufw's `before.rules` style. For the headless base there is no ufw: nftables only.

## 4. Tier 3 community mesh (separate project, off by default)

| Project | Runs on Linux x86? | Maturity / 2026 status | Exit-traffic exposure |
|---|---|---|---|
| Yggdrasil | yes, `yggdrasil` 0.5.15 in Arch extra, Jun-Oct 2026 releases [V] | alpha/experimental, unaudited [S] | none by design (overlay IPv6, no internet exit) |
| cjdns | yes, `cjdns` 22.3 in Arch extra [V] | old, low activity [U] | none |
| Reticulum (RNS) | yes, Python (`pip install rns`), not in official Arch repos [V: not found] | active hobbyist/off-grid; works over LoRa/Wi-Fi/Ethernet [U], 2026 status not confirmed | none |
| Tor relay/bridge | yes, `tor` 0.4.9.14 [V] | mature | non-exit relay/bridge: low. Exit relay: EFF says legal but attracts complaints/litigants/law enforcement and recommends not running exits from a home IP; operator monitoring can create wiretap liability [S: torproject.org/eff/tor-legal-faq mirror; FAQ revisions 2014/2020/2023, date unconfirmed] |
| Althea (rita) | `rita` Rust, Apache-2.0, repo updated 2026-06-09 [S]; company pivoted to Althea L1 chain, ~10 staff [S: blog.althea.net 2025 review, Tracxn] | commercial ISP-in-a-box, not a drop-in package, not in Arch repos [U] | paying exit nodes: legal exposure sits with the exit operator |
| Nym | NymVPN / mixnet client; not in official Arch repos [V] | 2026 status not found [U] | mixnet exit gateways carry exit risk |
| Helium | hotspots are LoRaWAN / CBRS radios on dedicated hardware [U]; not software for an x86 PC | 2026 status not found [U] | n/a |

Default stance: ship nothing from tier 3 in the base image. If built later, only non-exit roles (Yggdrasil peer, Tor non-exit relay/bridge, Reticulum transport) behind a double opt-in; never exit nodes on customer IPs.

## 5. Packaging

Arch / Omarchy 4.x (all [V] present in official repos unless noted):
- Tier 1: `tailscale` (or `headscale`, `nebula`), `wireguard-tools`, `nftables`
- Tier 2: `hostapd` `iw` `dnsmasq` `nftables` `iproute2` (has `tc`) `unbound` `wireless-regdb` (already in Omarchy base) `iperf3`
- Optional/test: `batctl`, `yggdrasil`, `tor`, `cjdns`
- AUR: none required. Reticulum via `pipx install rns` [U]. AUR RPC lookups for tailscale/headscale/nebula returned nothing because they are in extra [V].
- Omarchy + NM: keep desktop Wi-Fi on `wlan0` (NM-managed), give hostapd a dedicated card or virtual interface, and tell NM to ignore it: `/etc/NetworkManager/conf.d/90-pai-guest.conf` -> `[keyfile]\nunmanaged-devices=interface-name:wlan-ap`; also `[device]\nwifi.scan-rand-mac-address=no` [S: morrownr AP guide]. Virtual AP on the same card: `iw dev wlan0 interface add wlan-ap type __ap` works only if `iw list` combos allow managed+AP on one channel [U]. Dedicated second USB adapter is the clean path on the Dev image. `omarchy-restart-wifi` runs `nmcli radio wifi on`: it will not touch an unmanaged interface [V script, behavior U].
- Regdomain on Arch: `iw reg set US` at boot (unit) + hostapd `country_code=US`; `wireless-regdb` 2026.09.03 is in core [V]. CRDA is obsolete [U].

Fedora CoreOS / bootc (dnf/rpm-ostree) and Ubuntu Server (apt), names [U unless noted; all standard]:
- Fedora: `rpm-ostree install hostapd dnsmasq nftables iw wireguard-tools batctl iperf3 unbound wireless-regdb iproute-tc` + Tailscale from `pkgs.tailscale.com` repo. Bootc: put these in the Containerfile `dnf install`. FCOS base is minimal and may not carry Wi-Fi firmware/NetworkManager-wifi [U]: verify `lspci`, `dmesg | grep -i firmware`; layering `linux-firmware`/`NetworkManager-wifi` if needed.
- Ubuntu Server/Core: `apt install hostapd dnsmasq nftables iw wireguard-tools batctl iperf3 unbound wireless-regdb linux-firmware iproute2` + tailscale apt repo. `hostapd` package ships masked: `systemctl unmask hostapd` [S: morrownr guide]. Use `systemd-networkd` for the bridge (the same guide does).
- Kernel options on Fedora rawhide config all `=m/=y` as in section 0 [V]; Fedora stable/CoreOS use the same options [U]. Ubuntu [U].

## 6. Install sketch (Ansible style, same for both OS families with a package map)

```yaml
# group_vars/arch.yml
pai_pkgs_t1: [tailscale, wireguard-tools, nftables]
pai_pkgs_t2: [hostapd, iw, dnsmasq, iproute2, unbound, wireless-regdb, iperf3]
# group_vars/fedora.yml  (rpm-ostree: use community.general.rpm_ostree_pkg)
pai_pkgs_t1: [tailscale, wireguard-tools, nftables]
pai_pkgs_t2: [hostapd, iw, dnsmasq, iproute-tc, unbound, wireless-regdb, iperf3]
# group_vars/ubuntu.yml
pai_pkgs_t1: [tailscale, wireguard-tools, nftables]
pai_pkgs_t2: [hostapd, iw, dnsmasq, iproute2, unbound, wireless-regdb, linux-firmware, iperf3]

- hosts: pai
  become: true
  tasks:
    - name: tier 1 packages
      ansible.builtin.package: { name: "{{ pai_pkgs_t1 }}", state: present }
    - name: tailscaled
      ansible.builtin.systemd: { name: tailscaled, enabled: true, state: started }
    # join: tailscale up --login-server=<headscale-url> --authkey=<per-device key from PAI backend>  (never in repo)
    - name: tier 2 packages
      ansible.builtin.package: { name: "{{ pai_pkgs_t2 }}", state: present }
      when: pai_guest_capable | default(false)
    - name: NM must ignore the AP interface (Omarchy)
      ansible.builtin.copy:
        dest: /etc/NetworkManager/conf.d/90-pai-guest.conf
        content: "[keyfile]\nunmanaged-devices=interface-name:wlan-ap\n"
      when: ansible_os_family == "Archlinux"
    - ansible.builtin.template: { src: hostapd-guest.conf.j2, dest: /etc/hostapd/hostapd-guest.conf }
    - ansible.builtin.template: { src: dnsmasq-guest.conf.j2, dest: /etc/dnsmasq.d/pai-guest.conf }
    - ansible.builtin.template: { src: pai-guest.nft.j2,     dest: /etc/nftables.d/pai-guest.nft }
    - ansible.builtin.template: { src: 10-br-guest.netdev.j2, dest: /etc/systemd/network/10-br-guest.netdev }
    - ansible.builtin.template: { src: 20-br-guest.network.j2, dest: /etc/systemd/network/20-br-guest.network }
    - ansible.builtin.copy: { dest: /etc/sysctl.d/90-pai-guest.conf, content: "net.ipv4.ip_forward=1\n" }
    - name: units (installed but NOT enabled: guest is opt-in)
      ansible.builtin.copy: { src: "{{ item }}", dest: "/etc/systemd/system/{{ item }}" }
      loop: [pai-guest.target, pai-guest-hostapd.service, pai-guest-nft.service, pai-guest-shape.service, pai-guest-quota.timer]
```
Paths/units: `/etc/hostapd/hostapd-guest.conf`, `/etc/dnsmasq.d/pai-guest.conf`, `/etc/nftables.d/pai-guest.nft`, `/etc/systemd/network/*br-guest*`, `/etc/pai/guest.toml`, `/var/lib/pai/guest.enabled`. Enabling = owner action in the PAI app, which touches the flag file and runs `systemctl start pai-guest.target`.

Test checklist (run on every candidate card/box, record in `pai-bench`):
1. `lspci -nnk | grep -A3 -i network` (chipset + driver), `dmesg | grep -iE 'firmware|mt79|iwlwifi'`.
2. `iw list`: "AP" and "mesh point" under supported modes; copy the "valid interface combinations" block and note `#channels`; confirm 5 GHz non-DFS channels not flagged NO-IR after `iw reg set US`.
3. `hostapd -dd hostapd-guest.conf`: starts on ch 36/149 at 80 MHz, 11ax; phone joins with WPA3/WPA2.
4. Throughput: `iperf3 -s` on the box LAN side, phone/laptop client `iperf3 -c 10.77.0.1`, then through the AP to a LAN/Internet server (`-R` too); record Mbps at 1 m and 10 m, 5 GHz and 2.4 GHz. Compare to cap setting (within ~10%).
5. Isolation (from a guest laptop): cannot ping/arp the other guest (ap_isolate); `nmap -Pn 192.168.0.0/16 10.0.0.0/8 100.64.0.0/10` finds nothing; `curl http://10.77.0.1:<PAI API port>` and `ssh 10.77.0.1` fail; `curl http://<box LAN IP>:<PAI port>` fails; DNS resolves via 10.77.0.1; IPv6 gives no route; box can still reach the owner's tailnet.
6. Kill switch: `systemctl stop pai-guest.target` drops associations within 2 s, SSID disappears from a scan, nft table gone, desktop Wi-Fi/Ethernet unaffected; reboot with flag absent = AP stays off.
7. Caps: `iperf3 -P 8` from one guest limited to cap; two guests share fairly (CAKE `dual-dsthost`); quota timer cuts at N GB.
8. Coexistence: Omarchy desktop Wi-Fi/NM and Tailscale stay up during AP start/stop; on Omarchy verify ufw doesn't drop forwarded guest traffic.
9. Soak: 24 h, 10 clients, temperature and no hostapd restarts.

## 7. Legal, ISP, regulatory flags (non-legal-advice; get counsel before enabling by default)

- Default OFF for tier 2 and 3 is the right call: owner opt-in, plain-language terms, kill switch visible.
- FCC / regulatory domain: US units must run `country_code=US` and the owner must not be able to pick a looser country; DFS radar detection (`ieee80211h`) must work or stay on non-DFS channels; 6 GHz AP: standard-power needs AFC, indoor low-power only otherwise; Linux regdb marks 6 GHz channels no-IR on client-only cards [S]. FCC adopted geofenced variable-power 6 GHz rules in U-NII-5/7 effective 2026-04-27 [S: Federal Register 2026-03744], not applicable to our AP use. Whether the M.2 card's/OEM's FCC grant covers software-enabled AP mode, and whether PAI as the seller must re-certify, is an open compliance question [U]: ask the mini PC OEM and a test lab/counsel; Intel/MediaTek M.2 modules are usually certified as client modules.
- ISP terms: many residential plans prohibit resale/sharing or "servers" [U general]. Check the target ISPs' acceptable-use terms before marketing guest sharing; business tiers usually allow it.
- Liability: the account holder's IP appears on all guest traffic (copyright notices go to the account holder; DMCA safe-harbor eligibility, CALEA, state laws vary) [U]. Mitigate: WPA3 password per guest or voucher, short-lived access, captive-portal acceptable-use acceptance, DNS filtering, port blocks (SMTP 25, SMB, SSH optional), minimal-logging policy decided with counsel (logging helps abuse response, hurts privacy; EFF warns about wiretap exposure for affirmative monitoring [S]).
- Tier 3: no exit traffic on customer IPs; no payments/token features (Althea/Helium/Nym style) without securities/money-transmitter review; mesh relay of third-party traffic can breach the ISP terms above.
- Encryption/export: shipping WireGuard/Tailscale in hardware sold abroad touches export classification (EAR 5D002 mass-market) [U]: confirm with counsel before Kickstarter international shipping.

## Gaps to close next
Run `iw list` on a real sample (K11/Strix Halo) and fill sections 2 and 6 with measured values; confirm Omarchy `iwd` presence on the Dev image; confirm FCOS Wi-Fi firmware; confirm Tailscale ToS for bundling; verify nft/tc syntax on a live box.
