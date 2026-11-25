#!/bin/sh
# Builds the allowlist, then runs squid in the foreground. Lines that are not plain host names are dropped,
# so a bad entry can never widen the list (a leading dot would be a wildcard).
set -eu
mkdir -p /run/egress
{ [ -f /shared/egress-allowlist.txt ] && cat /shared/egress-allowlist.txt; printf '%s\n' ${PAI_EGRESS_ALLOW:-}; } 2>/dev/null \
  | tr 'A-Z' 'a-z' | grep -Ex '[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*' | sort -u > /run/egress/allow.txt || true
echo "egress allowlist: $(tr '\n' ' ' < /run/egress/allow.txt)" >&2
# squid drops to the unprivileged proxy user and cannot write to the container's stdout, so follow its log file.
touch /var/log/squid/access.log && chown proxy:proxy /var/log/squid/access.log
tail -F /var/log/squid/access.log &
exec squid -N -f /etc/squid/squid.conf
