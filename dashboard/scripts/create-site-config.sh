#!/bin/bash
# This script is designed to be run by create-instance.sh to generate
# a site-config.json file for ADDMAN dynamically.

set -e

TITLE=$1
DB_ID=$2
TARGET_DIR=$3

echo "Title: $TITLE"
echo "DB_ID: $DB_ID"
echo "Target dir: $TARGET_DIR"

if [ -z "$TARGET_DIR" ]; then
    echo "Target directory not provided"
    exit 1
fi

echo "Creating site-config.json at '$TARGET_DIR/site-config.json'..."

cat > "$TARGET_DIR/site-config.json" <<EOF
{
  "title": "$TITLE",
  "db_id": "$DB_ID",
  "uid_counter": "1054"
}
EOF
