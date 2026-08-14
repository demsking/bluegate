#!/bin/sh
set -eu

NODES_JSON=${UI_NODES_JSON:-'[{"id":"local","name":"Local node","apiBaseUrl":"http://127.0.0.1:8765"}]'}
DEFAULT_NODE_ID=${UI_DEFAULT_NODE_ID:-local}

cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.__BLUEGATE_UI_CONFIG__ = {
  nodes: ${NODES_JSON},
  defaultNodeId: "${DEFAULT_NODE_ID}",
};
EOF

exec nginx -g 'daemon off;'
