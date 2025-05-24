#!/bin/bash

APP_NAME=$1

docker run --rm -d --network path-deployments-net \
    --name $APP_NAME \
    -e DJANGO_APP_NAME=$APP_NAME \
    --label traefik.enable=true \
    --label traefik.http.routers.$APP_NAME-router.rule="PathPrefix(\"/$APP_NAME\")" \
    --label traefik.http.middlewares.$APP_NAME-strip.stripprefix.prefixes=/$APP_NAME \
    --label traefik.http.routers.$APP_NAME-router.middlewares=$APP_NAME-strip@docker \
    --label traefik.http.services.$APP_NAME-service.loadbalancer.server.port=8000 \
    path-deployments-app
