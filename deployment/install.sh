#!/bin/bash
set -euo pipefail

APP_DIR="/opt/cyberscope"
VENV_DIR="$APP_DIR/venv"
SERVICE_FILE="/etc/systemd/system/cyberscope.service"

if [[ $EUID -ne 0 ]]; then
  echo "This script must be run as root" >&2
  exit 1
fi

echo "Creating application directory at $APP_DIR"
install -d -m 755 "$APP_DIR"
cp -r dashboard_backend "$APP_DIR/dashboard-backend"

python3.11 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

pip install --upgrade pip
pip install -r "$APP_DIR/dashboard-backend/requirements.txt"

pushd "$APP_DIR/dashboard-backend" >/dev/null
python - <<'PY'
from dashboard_backend.utils.database import init_db
import asyncio

asyncio.run(init_db())
PY
popd >/dev/null

cp deployment/cyberscope.service "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable cyberscope.service
systemctl restart cyberscope.service

echo "Reloading nginx configuration"
cp deployment/nginx-cyberscope.conf /etc/nginx/sites-enabled/cyberscope.conf
nginx -t && systemctl reload nginx

echo "Installation completed."
