#!/bin/sh

set -eu

if [ ! -f /app/config.toml ]; then
    cp /app/config.example.toml /app/config.toml
    echo "config.toml not found, created /app/config.toml from config.example.toml"
fi

mkdir -p /app/downloads

# 后台启动 Web UI
poetry run python web_main.py > /tmp/web.log 2>&1 &
WEB_PID=$!
echo "Web UI started on http://0.0.0.0:9527"
echo "CLI: docker exec -it amd-all poetry run python main.py"
echo ""

# 保持容器运行（等待 Web UI）
wait $WEB_PID
