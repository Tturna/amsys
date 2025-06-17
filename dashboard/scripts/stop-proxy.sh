#!/bin/bash

docker ps --format='{{json .Names}}' | grep -q "amsys-traefik" > /dev/null

if [[ $? != 0 ]]; then
    echo "Proxy is not running."
    exit 1
fi

docker compose -f ../proxy/compose-traefik.yaml down

echo "Proxy stopped"
