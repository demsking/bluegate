#!/bin/sh
set -eu

NODES_JSON=${BLUEGATE_NODES_JSON:-'[]'}

PROXY_LOCATIONS_FILE=/etc/nginx/proxy-locations.inc
PUBLIC_NODES_FILE=/usr/share/nginx/html/nodes.json

if ! printf '%s' "$NODES_JSON" | jq -e 'type == "array"' >/dev/null 2>&1; then
  echo "BLUEGATE_NODES_JSON must be a JSON array" >&2
  exit 1
fi

: > "$PROXY_LOCATIONS_FILE"

node_count=$(printf '%s' "$NODES_JSON" | jq 'length')

node_index=0
while [ "$node_index" -lt "$node_count" ]; do
  node_id=$(printf '%s' "$NODES_JSON" | jq -r ".[$node_index].id // empty")
  node_name=$(printf '%s' "$NODES_JSON" | jq -r ".[$node_index].name // empty")
  node_server=$(printf '%s' "$NODES_JSON" | jq -r ".[$node_index].server // empty")

  if [ -z "$node_id" ] || [ -z "$node_name" ] || [ -z "$node_server" ]; then
    echo "Each BLUEGATE_NODES_JSON item must include non-empty id, name, and server" >&2
    exit 1
  fi

  case "$node_id" in
    *[!A-Za-z0-9._~-]*)
      echo "Invalid node id '$node_id'. Allowed: A-Z a-z 0-9 . _ ~ -" >&2
      exit 1
      ;;
  esac

  normalized_server=${node_server%/}

  cat >> "$PROXY_LOCATIONS_FILE" <<EOF
  location /$node_id/ {
    proxy_pass $normalized_server/;
    proxy_http_version 1.1;
    proxy_set_header Host \$host;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Host \$host;
    proxy_set_header Upgrade \$http_upgrade;
    proxy_set_header Connection "upgrade";
  }

EOF

  node_index=$((node_index + 1))
done

printf '%s' "$NODES_JSON" | jq -c '[.[] | {id, name}]' > "$PUBLIC_NODES_FILE"

exec nginx -g 'daemon off;'
