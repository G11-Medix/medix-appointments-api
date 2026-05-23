#!/bin/sh
set -e

# Start cloudflared tunnel according to provided environment variables.
# Priority: CLOUDFLARED_CMD > CLOUDFLARED_TOKEN > CLOUDFLARED_URL > default to local port
if [ -n "$CLOUDFLARED_CMD" ]; then
  sh -c "$CLOUDFLARED_CMD" &
elif [ -n "$CLOUDFLARED_TOKEN" ]; then
  cloudflared tunnel --no-autoupdate run --token "$CLOUDFLARED_TOKEN" &
elif [ -n "$CLOUDFLARED_URL" ]; then
  cloudflared tunnel --url "$CLOUDFLARED_URL" --no-autoupdate &
else
  cloudflared tunnel --url http://127.0.0.1:8001 --no-autoupdate &
fi

# small delay to let cloudflared start
sleep 1

exec uvicorn app.main:app --host 0.0.0.0 --port 8001
