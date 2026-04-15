#!/usr/bin/env bash
# Wait for Klipper to reach "ready" state via Moonraker API.
# Usage: wait_for_ready.sh [timeout_seconds]

TIMEOUT=${1:-30}

echo "Waiting for Klipper to become ready..."
for i in $(seq 1 "$TIMEOUT"); do
    state=$(curl -s http://localhost:7125/printer/info 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['result']['state'])" 2>/dev/null)
    if [ "$state" = "ready" ]; then
        echo "Printer ready."
        exit 0
    fi
    sleep 1
done

echo "Printer did not become ready in ${TIMEOUT}s (last state: ${state:-unknown})."
exit 1
