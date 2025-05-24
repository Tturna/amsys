#!/bin/bash

APP_NAME=$1

docker run --rm -d --network path-deployments-net \
    --name $APP_NAME \
    -e DJANGO_APP_NAME=$APP_NAME \
    path-deployments-app
