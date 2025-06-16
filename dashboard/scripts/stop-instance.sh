#!/bin/bash
# This script is designed to be executed automatically

APP_NAME=$1

if [ -z $APP_NAME ]; then
    echo "App name not provided."
    exit 1
fi

if [[ ! "$APP_NAME" =~ ^[a-zA-Z0-9_-]+$ ]]; then
  echo "Error: APP_NAME contains invalid characters."
  exit 1
fi

BASE_PATH="$(realpath "$(pwd)/..")"

if [ -z "$AMSYS_INSTANCE_BASE_PATH" ]; then
    AMSYS_INSTANCE_BASE_PATH=$BASE_PATH
fi

TARGET_DIR="$(realpath "$AMSYS_INSTANCE_BASE_PATH/$APP_NAME")"

echo "Looking for app '$TARGET_DIR'..."

# Check if TARGET_DIR is not inside BASE_DIR (traversal attack)
case "$TARGET_DIR" in
  "$AMSYS_INSTANCE_BASE_PATH"/*) ;;  # do nothing
  *)
    echo "Error: target directory is outside of base directory!"
    exit 1
    ;;
esac

if [[ $TARGET_DIR == "$(realpath "$(pwd)")" ]]; then
    echo "Can't stop the dashboard itself."
    exit 1
fi

if [[ $TARGET_DIR == "$(realpath "$(pwd)/../proxy")" ]]; then
    echo "Can't stop the proxy service."
    exit 1
fi

if [ -d "$TARGET_DIR" ]; then
    docker ps --format='{{json .Names}}' | grep -q "$APP_NAME" > /dev/null

    if [[ $? == 0 ]]; then
        echo "Found $APP_NAME. Stopping..."
        docker container stop $APP_NAME
    else
        echo "Couldn't find a running Docker container named $APP_NAME."
        exit 1
    fi
else
    echo "$TARGET_DIR not found."
    exit 1
fi

echo "$APP_NAME stopped."
