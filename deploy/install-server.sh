#!/usr/bin/env bash
set -euo pipefail

APP_ROOT=/opt/czlife
SERVICE_USER=czlife

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home "$APP_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"
fi

install -d -o "$SERVICE_USER" -g "$SERVICE_USER" "$APP_ROOT"
install -d -m 0750 -o root -g "$SERVICE_USER" /etc/czlife
install -m 0644 deploy/czlife-api.service /etc/systemd/system/czlife-api.service
install -m 0644 deploy/czlife-worker.service /etc/systemd/system/czlife-worker.service

echo "Create /etc/czlife/czlife.env before enabling services."
echo "Then run: systemctl daemon-reload && systemctl enable --now czlife-api czlife-worker"

