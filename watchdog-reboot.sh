#!/bin/bash

URL=$HEATING_URL
MAX_TIME=5
INTERVAL=300

while true
do
    response_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time $MAX_TIME "$URL")

    if [ "$response_code" -ne 200 ]; then
        echo "Non-200 response code received. Rebooting the machine."
        sudo reboot
    fi

    sleep $INTERVAL  # Sleep for 5 minutes before the next request
done