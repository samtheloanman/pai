#!/bin/sh
# Builds the allowlist, runs squid in the foreground, and reloads squid when the allowlist changes.
# Lines that are not plain host names are dropped, so a bad entry can never widen the list (a leading dot
# would be a wildcard).
set -eu
mkdir -p /run/egress
build() {
  { [ -f /shared/egress-allowlist.txt ] && cat /shared/egress-allowlist.txt; printf '%s\n' ${PAI_EGRESS_ALLOW:-}; } 2>/dev/null \
    | tr 'A-Z' 'a-z' | grep -Ex '[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*' | sort -u || true
}
build > /run/egress/allow.txt
echo "egress allowlist: $(tr '\n' ' ' < /run/egress/allow.txt)" >&2
# squid drops to the unprivileged proxy user and cannot write to the container's stdout, so follow its log file.
touch /var/log/squid/access.log && chown proxy:proxy /var/log/squid/access.log
tail -F /var/log/squid/access.log &
# The app rewrites /shared/egress-allowlist.txt when the owner changes providers. squid becomes PID 1 below.
( while sleep 5; do
    build > /run/egress/allow.new
    if ! cmp -s /run/egress/allow.new /run/egress/allow.txt; then
      mv /run/egress/allow.new /run/egress/allow.txt
      echo "egress allowlist changed: $(tr '\n' ' ' < /run/egress/allow.txt)" >&2
      kill -HUP 1
    fi
  done ) &
exec squid -N -f /etc/squid/squid.conf
