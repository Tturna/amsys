#!/bin/bash

set -e

APP_NAME=$1

docker container stop $APP_NAME
