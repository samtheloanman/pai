# PAI private remote access

**Goal:** reach your PAI box from your phone or laptop, from anywhere, without opening a port to the internet.

This replaces an earlier design that made the PAI box an exit node and a router for the whole home network. That design is withdrawn: it gave every device on the private network a path into the home LAN, turned on remote shell access, and conflicts with PRD requirement LAN-2 (PAI does not carry other devices' traffic in the MVP).

## How it works

```
  phone / laptop  ──── encrypted private network (WireGuard) ────  PAI box
  (Tailscale app)                                                  tailscale serve :443
                                                                        │
                                                                        ▼
                                                              PAI app on 127.0.0.1:8088
```

- The PAI app listens on `127.0.0.1` only. Nothing listens on the home network or the internet.
- `tailscale serve` publishes the app to your private network over HTTPS. Only devices you added to that network can reach it.
- The box is not an exit node, does not route your LAN, and does not run Tailscale SSH. Funnel (publishing to the internet) is never used.

## Choose a coordinator

| Option | When | Setting |
|---|---|---|
| Tailscale account (default) | Easiest. Tailscale's servers introduce your devices to each other; they cannot read the traffic. | none |
| Headscale (self-hosted) | You want no outside company involved. You run the coordinator yourself. | `PAI_LOGIN_SERVER=https://your-headscale-host` |

## Set up the box

Linux, as root. Install Tailscale from your distribution's repositories or the signed repository at <https://tailscale.com/download/linux>. The script installs the package if your repositories already carry it; it never downloads and runs an install script.

```bash
cd prototype

# 1. Join the private network. On a box with no screen, give it a pre-auth key file.
sudo TS_AUTHKEY_FILE=/root/ts-authkey ./setup-pai-vpn-gateway.sh up

# 2. Publish the PAI app to the private network.
sudo ./setup-pai-vpn-gateway.sh serve

# 3. Check it.
./verify-vpn-tunnel.sh
```

`serve` refuses to publish while the app has no login, because every device on your private network could then read and change your data. Owner login is the next piece of work (see the plan in `docs/superpowers/plans/`). To publish anyway on a private network that holds only your own devices, set `PAI_SERVE_WITHOUT_LOGIN=1`.

Add `--dry-run` to any command to print what it would run.

## Set up your phone or laptop

1. Install the Tailscale app and sign in to the same account (or point it at your Headscale server).
2. Open `https://<box-name>.<your-network>.ts.net`. The exact address is printed by `tailscale serve status` on the box.
3. Do not select the PAI box as an exit node. It is not one.

## What the check covers

`verify-vpn-tunnel.sh` exits non-zero if any of these fail:

1. The box is connected to the private network.
2. It advertises no exit node and no LAN routes, and Tailscale SSH is off.
3. Funnel is off.
4. The app port is bound to loopback only, and the app answers there.
5. Only the PAI app is published, and its private HTTPS address answers.
6. If the app is published, its data routes refuse a request with no login.

It contacts no outside service.

## Undo

```bash
sudo ./setup-pai-vpn-gateway.sh down
```

This unpublishes the app and disconnects. It also removes what the earlier version of the script set up: the settings file `/etc/sysctl.d/99-pai-vpn.conf` and its NAT and forwarding rules. Packet forwarding itself is left on, because Docker needs it; without the NAT rules and the advertised routes the box no longer routes for other devices.

## Not in this version

- Blocking ads or trackers for other devices on your network (needs PAI to be the router; open decision, PRD LAN-2).
- Using the box as a VPN exit for your phone's internet traffic.
