#!/bin/bash

set -e

APP_NAME=$1
URL_PATH=$2
APP_TITLE=$3
API_TOKEN=$4
APP_ID=$5

echo "App ID: $APP_ID"
echo "API Token: $API_TOKEN"

docker run -d --network path-deployments-net \
    --name $APP_NAME \
    -e DJANGO_URL_PATH=$URL_PATH \
    -e API_TOKEN=$API_TOKEN \
    --label traefik.enable=true \
    --label traefik.http.routers.$APP_NAME-router.rule="PathPrefix(\"/$URL_PATH\")" \
    --label traefik.http.middlewares.$APP_NAME-strip.stripprefix.prefixes=/$URL_PATH \
    --label traefik.http.routers.$APP_NAME-router.middlewares=$APP_NAME-strip@docker \
    --label traefik.http.services.$APP_NAME-service.loadbalancer.server.port=8000 \
    path-deployments-app
