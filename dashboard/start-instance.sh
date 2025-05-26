#!/bin/bash

set -e

APP_NAME=$1
URL_PATH=$2

docker run --rm -d --network path-deployments-net \
    --name $APP_NAME \
    -e DJANGO_URL_PATH=$URL_PATH \
    --label traefik.enable=true \
    --label traefik.http.routers.$APP_NAME-router.rule="PathPrefix(\"/$URL_PATH\")" \
    --label traefik.http.middlewares.$APP_NAME-strip.stripprefix.prefixes=/$URL_PATH \
    --label traefik.http.routers.$APP_NAME-router.middlewares=$APP_NAME-strip@docker \
    --label traefik.http.services.$APP_NAME-service.loadbalancer.server.port=8000 \
    path-deployments-app
