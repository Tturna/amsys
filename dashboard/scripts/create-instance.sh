#!/bin/bash
# This script is designed to be executed automatically by a master dashboard app

set -e

APP_NAME=$1
URL_PATH=$2     # same as app name if not set
APP_TITLE=$3    # title for ADDMAN login and nav bar
API_TOKEN=$4    # for master dashboard API auth
APP_ID=$5       # for master dashboard API auth

if [ -z "$APP_NAME" ]; then
    echo "No app name provided."
    exit 1
fi

if [[ ! "$APP_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
    echo "Error: APP_NAME contains invalid characters."
    exit 1
fi

echo "Using app name '$APP_NAME'."

if [ -z "$URL_PATH" ]; then
    echo "No URL path provided. Using app name ($APP_NAME)."
    URL_PATH=$APP_NAME
else
    echo "Using URL path '$URL_PATH'."
fi

if [ -z "$APP_TITLE" ]; then
    echo "No app title path provided. Using app name ($APP_NAME)."
    APP_TITLE=$APP_NAME
else
    echo "Using app title '$APP_TITLE'."
fi

if [ -z "$API_TOKEN" ]; then
    echo "No API token provided."
    exit 1
fi

if [ -z "$APP_ID" ]; then
    echo "No app ID provided."
    exit 1
fi

if [ -z "$AMSYS_INSTANCE_BASE_PATH" ]; then
    echo "No instance base path set in environment. Falling back to '$(realpath "$(pwd)")/../'"
    AMSYS_INSTANCE_BASE_PATH="$(realpath "$(pwd)/..")"
else
    echo "Using instance base path '$AMSYS_INSTANCE_BASE_PATH'."
fi

INSTANCE_PATH="$AMSYS_INSTANCE_BASE_PATH/$APP_NAME"

if [ -d "$INSTANCE_PATH" ]; then
    echo "Directory $INSTANCE_PATH already exists. An app with the name '$APP_NAME' is probably already created."
    exit 1
fi

mkdir "$INSTANCE_PATH"
mkdir "$INSTANCE_PATH/Database"
mkdir "$INSTANCE_PATH/uploads"
mkdir "$INSTANCE_PATH/mailbox"
mkdir "$INSTANCE_PATH/mailbox/receive"
mkdir "$INSTANCE_PATH/mailbox/share"

echo "Creating site config..."
#                       title,       db_id,      target directory
./scripts/create-site-config.sh "$APP_TITLE" "$APP_NAME" "$INSTANCE_PATH"

echo "Site config created."
echo "Copying other config files..."

cp ./templates/settings_production.py $INSTANCE_PATH/settings_production.py
cp ./templates/sshd_config $INSTANCE_PATH/sshd_config
echo "Running container..."

docker run -d --network addman-testing-net --name $APP_NAME \
    --label traefik.enable=true \
    --label "traefik.http.routers.$APP_NAME-router.rule=PathPrefix(\"/$URL_PATH\")" \
    --label traefik.http.services."$APP_NAME"-service.loadbalancer.server.port=8000 \
    --label traefik.http.middlewares."$APP_NAME"-strip.stripprefix.prefixes=/"$URL_PATH" \
    --label traefik.http.routers."$APP_NAME"-router.middlewares=$APP_NAME-strip@docker \
    -v "$INSTANCE_PATH"/Database:/addman/3D-Repository/Database \
    -v "$INSTANCE_PATH"/uploads:/addman/uploads \
    -v "$INSTANCE_PATH"/mailbox:/addman/3D-Repository/mailbox \
    -v "$INSTANCE_PATH"/site-config.json:/addman/3D-Repository/site-config.json \
    -v "$INSTANCE_PATH"/settings_production.py:/addman/3D-Repository/3D-Repository/settings_production.py \
    -v "$INSTANCE_PATH"/sshd_config:/etc/ssh/sshd_config \
    -v ./ssh/instance_ca.pub:/etc/ssh/instance_ca.pub \
    -e ADDMAN_APP_NAME="$APP_NAME" \
    -e ADDMAN_API_TOKEN="$API_TOKEN" \
    -e ADDMAN_APP_ID="$APP_ID" \
    addman

echo "Instance created."
