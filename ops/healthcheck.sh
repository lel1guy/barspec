#!/usr/bin/env bash
# Health watchdog for the live BarSpec service.
# Silent (exit 0) when healthy; loud (exit 1) when the app stops answering —
# a non-zero exit makes the Hermes cron alert fire.
CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 http://192.168.1.77:8777/api/auth/status)
if [ "$CODE" = "200" ]; then
  exit 0
fi
echo "Barspec DOWN on :8777 (HTTP $CODE) — $(date '+%F %T')"
exit 1
