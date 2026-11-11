#!/bin/bash
# Public tunnel for vf-mcp + allowlist maintenance.
# localtunnel URLs rotate unless --subdomain holds; this wrapper parses the
# live URL, writes it to .vf-http.env, and restarts vf-mcp so the MCP
# Host allowlist always matches the public name. Run under systemd
# (vf-mcp-tunnel.service, Restart=always). Never pkill by pattern here.
set -u
cd /home/ubuntu/videofactory
SUBDOMAIN="${VF_SUBDOMAIN:-vfshastra}"
ENVFILE=/home/ubuntu/videofactory/.vf-http.env
LOG=/tmp/mcp_public.log
ARGS="--port 8930"
[ -n "$SUBDOMAIN" ] && ARGS="$ARGS --subdomain $SUBDOMAIN"
echo "$(date -u +%FT%TZ) starting localtunnel $ARGS" >> "$LOG"
/usr/bin/npx -y localtunnel $ARGS > /tmp/lt.url.log 2>&1 &
LT=$!
for i in $(seq 1 30); do
  URL=$(grep -oE "https://[a-z0-9.-]+\.loca\.lt" /tmp/lt.url.log 2>/dev/null | head -n 1)
  if [ -n "$URL" ]; then break; fi
  sleep 2
done
if [ -z "${URL:-}" ]; then
  echo "$(date -u +%FT%TZ) no URL from localtunnel, exiting for retry" >> "$LOG"
  kill $LT 2>/dev/null
  exit 1
fi
HOST=$(echo "$URL" | sed 's#https://##')
echo "VF_ALLOWED_HOSTS=$HOST" > "$ENVFILE"
echo "$(date -u +%FT%TZ) public at $URL/mcp, restarting vf-mcp" >> "$LOG"
sudo -n systemctl restart vf-mcp.service
wait $LT
