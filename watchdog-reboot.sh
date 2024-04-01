#!/bin/bash

set -e

if [ -x "$1" ]; then
        URL="$HEALTHCHECK_URL";
else
        URL=$1;
fi

if [ -z "$URL" ]; then
        echo "Usage: watchdog-reboot.sh <HEALTHCHECK_URL>"
        echo "or set 'HEALTHCHECK_URL' environment variable"
        exit 1
fi

REQUEST_TIMEOUT=5
INTERVAL=300

sleep $INTERVAL # Sleep before first check

while true
do
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $REQUEST_TIMEOUT "$URL")

    if [ "$response_code" -ne 200 ]; then
        echo "Non-200 response code received. Rebooting the machine."
        sudo reboot
    fi

    sleep $INTERVAL  # Sleep for 5 minutes before the next request
done
