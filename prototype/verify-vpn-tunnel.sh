#!/usr/bin/env bash
# Checks that a PAI box is reachable only over its private network. Run it on the box.
# Exits 0 when every check passes and 1 when any check fails. It calls no outside service.
#
#   ./verify-vpn-tunnel.sh
#   PAI_PEER=my-phone ./verify-vpn-tunnel.sh     also check that this device answers over the private network
#   PAI_PORT=8088                                 local port of the PAI app (default 8088)
set -uo pipefail

PORT="${PAI_PORT:-8088}"
FAILS=0
pass() { echo "  [PASS] $*"; }
fail() { echo "  [FAIL] $*"; FAILS=$((FAILS + 1)); }
skip() { echo "  [SKIP] $*"; }
# json <python expression over d>: reads JSON on stdin, prints the expression's value
json() { python3 -c 'import json,sys
d=json.load(sys.stdin)
print(eval(sys.argv[1]))' "$1" 2>/dev/null; }

for tool in tailscale python3 curl; do
  command -v "$tool" >/dev/null 2>&1 || { echo "[FAIL] '$tool' is required and was not found"; exit 1; }
done

echo "[1] Private network connection"
STATUS="$(tailscale status --json 2>/dev/null || true)"
STATE="$(printf '%s' "$STATUS" | json 'd.get("BackendState")')"
if [[ "$STATE" == "Running" ]]; then pass "connected"; else fail "not connected (state: ${STATE:-unknown}). Run setup-pai-vpn-gateway.sh up"; fi
DNSNAME="$(printf '%s' "$STATUS" | json '(d.get("Self") or {}).get("DNSName","").rstrip(".")')"

echo "[2] This box is not a router for other traffic"
PREFS="$(tailscale debug prefs 2>/dev/null || true)"
ROUTES="$(printf '%s' "$PREFS" | json 'len(d.get("AdvertiseRoutes") or [])')"
SSH="$(printf '%s' "$PREFS" | json 'bool(d.get("RunSSH"))')"
if [[ "$ROUTES" == "0" ]]; then pass "no exit node, no LAN routes advertised"; else fail "advertising ${ROUTES:-unknown} route(s) (exit node or LAN). Run setup-pai-vpn-gateway.sh up to clear them"; fi
if [[ "$SSH" == "False" ]]; then pass "Tailscale SSH is off"; else fail "Tailscale SSH is on (or could not be read)"; fi

echo "[3] Nothing is published to the internet"
FUNNEL="$(tailscale funnel status --json 2>/dev/null || echo '{}')"
OPEN="$(printf '%s' "${FUNNEL:-{\}}" | json 'sum(1 for v in (d.get("AllowFunnel") or {}).values() if v)')"
if [[ "$OPEN" == "0" ]]; then pass "Funnel is off"; else fail "Funnel is on: the app is reachable from the internet. Run: tailscale funnel reset"; fi

echo "[4] The PAI app listens on this box only"
if command -v ss >/dev/null 2>&1; then
  WIDE="$(ss -ltnH "sport = :$PORT" 2>/dev/null | awk '{print $4}' | grep -Ev '^(127\.0\.0\.1|\[::1\]):' || true)"
  if [[ -z "$WIDE" ]]; then pass "port $PORT is bound to loopback only"; else fail "port $PORT is open on: $(echo "$WIDE" | tr '\n' ' ')"; fi
else
  fail "'ss' not found, so the listening address could not be checked"
fi
CODE="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://127.0.0.1:$PORT/api/health" || true)"
if [[ "$CODE" == "200" ]]; then pass "app answers on 127.0.0.1:$PORT"; else fail "app does not answer on 127.0.0.1:$PORT (got ${CODE:-nothing})"; fi

echo "[5] Published address"
SERVE="$(tailscale serve status --json 2>/dev/null || echo '{}')"
TARGETS="$(printf '%s' "${SERVE:-{\}}" | json '" ".join(sorted({h.get("Proxy","") for w in (d.get("Web") or {}).values() for h in (w.get("Handlers") or {}).values()}))')"
if [[ -z "$TARGETS" ]]; then
  skip "the app is not published yet (setup-pai-vpn-gateway.sh serve)"
elif [[ "$TARGETS" == "http://127.0.0.1:$PORT" ]]; then
  pass "publishes only the PAI app"
  if [[ -n "$DNSNAME" ]]; then
    CODE="$(curl -s -o /dev/null -m 10 -w '%{http_code}' "https://$DNSNAME/api/health" || true)"
    if [[ "$CODE" == "200" ]]; then pass "https://$DNSNAME answers"; else fail "https://$DNSNAME does not answer (got ${CODE:-nothing})"; fi
  fi
else
  fail "publishes something other than the PAI app: $TARGETS"
fi

echo "[6] App login"
CODE="$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://127.0.0.1:$PORT/api/memories" || true)"
if [[ "$CODE" == "401" || "$CODE" == "403" ]]; then
  pass "data routes refuse a request with no login"
elif [[ -n "$TARGETS" ]]; then
  fail "the app is published but has no login: every device on the private network can use it"
else
  skip "the app has no login yet; it is not published, so only this box can reach it"
fi

if [[ -n "${PAI_PEER:-}" ]]; then
  echo "[7] Peer '$PAI_PEER'"
  if tailscale ping --c 2 --timeout 3s "$PAI_PEER" >/dev/null 2>&1; then pass "answers over the private network"; else fail "no answer over the private network"; fi
fi

echo
if [[ $FAILS -eq 0 ]]; then echo "All checks passed."; exit 0; fi
echo "$FAILS check(s) failed."
exit 1
