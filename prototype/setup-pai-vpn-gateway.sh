#!/usr/bin/env bash
# Private remote access for a PAI box (Linux), over Tailscale or a self-hosted Headscale.
#
# What it does: joins the box to your private network, and (on request) publishes the PAI app to that network
# only, over HTTPS. What it never does: act as an exit node, route your home LAN, turn on Tailscale SSH,
# open a port to the internet (no Funnel), or download and run an install script.
#
#   sudo ./setup-pai-vpn-gateway.sh up       join the private network
#   sudo ./setup-pai-vpn-gateway.sh serve    publish the PAI app to the private network (HTTPS)
#   sudo ./setup-pai-vpn-gateway.sh down     unpublish, leave the network, undo what older versions set up
#   add --dry-run to print the commands instead of running them
#
# Settings (environment):
#   TS_AUTHKEY_FILE     file holding a pre-auth key, so a headless box does not wait for a browser login
#   TS_AUTHKEY          the same key as a value; it is written to a private temp file, never put on a command line
#   PAI_LOGIN_SERVER    your Headscale URL (leave unset for a Tailscale account)
#   PAI_HOSTNAME        name of this box on the private network (default: pai)
#   PAI_PORT            local port of the PAI app (default: 8088)
#   TAILSCALE_VERSION   install exactly this package version when Tailscale is missing
#   PAI_SERVE_WITHOUT_LOGIN=1   publish even though the app has no login yet (every device on your private
#                               network could then use it)
set -euo pipefail

DRY=0; CMD=""; TMPKEY=""
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    up|serve|down) CMD="$a" ;;
    -h|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $a (try --help)" >&2; exit 2 ;;
  esac
done
CMD="${CMD:-up}"
PORT="${PAI_PORT:-8088}"
HOSTNAME_TS="${PAI_HOSTNAME:-pai}"
[[ "$PORT" =~ ^[0-9]{1,5}$ ]] || { echo "PAI_PORT must be a port number" >&2; exit 2; }
[[ "$HOSTNAME_TS" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]] || { echo "PAI_HOSTNAME must be a plain host name" >&2; exit 2; }

run() { if [[ $DRY -eq 1 ]]; then printf 'would run:'; printf ' %q' "$@"; printf '\n'; else "$@"; fi; }
die() { echo "[ERROR] $*" >&2; exit 1; }

if [[ $DRY -eq 0 ]]; then
  [[ "$(uname -s)" == "Linux" ]] || die "this script sets up a Linux PAI box"
  [[ $EUID -eq 0 ]] || die "run as root (sudo)"
fi

install_tailscale() {
  command -v tailscale >/dev/null 2>&1 && return 0
  echo "Tailscale is not installed. Installing the package from this system's configured repositories..."
  local v="${TAILSCALE_VERSION:-}"
  if command -v dnf >/dev/null 2>&1; then
    run dnf install -y "tailscale${v:+-$v}"
  elif command -v apt-get >/dev/null 2>&1; then
    run apt-get install -y "tailscale${v:+=$v}"
  else
    die "no dnf or apt-get found. Install Tailscale from https://tailscale.com/download/linux, then run this again."
  fi
  if [[ $DRY -eq 0 ]] && ! command -v tailscale >/dev/null 2>&1; then
    die "the tailscale package is not in this system's repositories. Add the signed repository from https://tailscale.com/download/linux (do not pipe a script into a shell), then run this again."
  fi
  run systemctl enable --now tailscaled
}

cmd_up() {
  install_tailscale
  local args=(up --reset --hostname "$HOSTNAME_TS" --accept-dns=false --accept-routes=false)
  [[ -n "${PAI_LOGIN_SERVER:-}" ]] && args+=(--login-server "$PAI_LOGIN_SERVER")
  local keyfile="${TS_AUTHKEY_FILE:-}"
  if [[ -z "$keyfile" && -n "${TS_AUTHKEY:-}" ]]; then
    TMPKEY="$(umask 077; mktemp)"; trap 'rm -f "$TMPKEY"' EXIT  # global: the trap runs after this function returns
    printf '%s' "$TS_AUTHKEY" > "$TMPKEY"; keyfile="$TMPKEY"
  fi
  if [[ -n "$keyfile" ]]; then
    [[ -r "$keyfile" ]] || die "cannot read the pre-auth key file: $keyfile"
    args+=(--auth-key "file:$keyfile")
  else
    echo "No pre-auth key given: Tailscale will print a login link. On a headless box set TS_AUTHKEY_FILE."
  fi
  # --reset clears anything an older version of this script turned on (exit node, LAN routes, Tailscale SSH).
  run tailscale "${args[@]}"
  echo "Joined the private network as '$HOSTNAME_TS'. Next: '$0 serve' publishes the PAI app to it."
}

app_has_login() {  # true when a data route refuses an anonymous request
  local code
  code="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://127.0.0.1:$PORT/api/memories" || true)"
  [[ "$code" == "401" || "$code" == "403" ]]
}

cmd_serve() {
  command -v tailscale >/dev/null 2>&1 || die "Tailscale is not installed. Run '$0 up' first."
  if [[ $DRY -eq 0 ]]; then
    curl -s -o /dev/null -m 5 "http://127.0.0.1:$PORT/api/health" || die "the PAI app is not answering on 127.0.0.1:$PORT"
    if ! app_has_login && [[ "${PAI_SERVE_WITHOUT_LOGIN:-0}" != "1" ]]; then
      die "the PAI app has no login yet, so every device on your private network could read and change it. Not published. To publish anyway, set PAI_SERVE_WITHOUT_LOGIN=1."
    fi
  fi
  run tailscale funnel reset
  run tailscale serve --bg --https=443 "http://127.0.0.1:$PORT"
  echo "Published to your private network only. Check it with ./verify-vpn-tunnel.sh"
}

cmd_down() {
  if command -v tailscale >/dev/null 2>&1; then
    run tailscale funnel reset
    run tailscale serve reset
    run tailscale down
  fi
  # Older versions of this script made the box a router for the whole LAN. Undo exactly those changes.
  # The settings file is removed; the live forwarding switch is left alone because Docker needs it on for
  # container networking. The removed settings stop applying at the next boot.
  if [[ -f /etc/sysctl.d/99-pai-vpn.conf || $DRY -eq 1 ]]; then
    run rm -f /etc/sysctl.d/99-pai-vpn.conf
  fi
  if command -v iptables >/dev/null 2>&1 && [[ $DRY -eq 0 ]]; then
    local wan; wan="$(ip route show default 2>/dev/null | awk '{print $5; exit}')"
    if [[ -n "$wan" ]]; then
      iptables -t nat -D POSTROUTING -o "$wan" -j MASQUERADE 2>/dev/null || true
    fi
    iptables -D FORWARD -i tailscale0 -j ACCEPT 2>/dev/null || true
  fi
  echo "Unpublished and disconnected. Run 'tailscale logout' to also remove this box from the network."
}

"cmd_$CMD"
