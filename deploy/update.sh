#!/usr/bin/env bash
# Update LKMS on the server to the latest code on GitHub. Run as the lkms user:
#   sudo -u lkms /srv/lkms/deploy/update.sh
# then restart the services as shown at the end.
set -euo pipefail
cd /srv/lkms

echo "Taking a backup first..."
(cd backend && .venv/bin/python manage.py backup --no-prune)

git pull --ff-only

cd backend
uv sync --frozen --no-dev
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy --fail-level ERROR

cd ../frontend
npm ci --no-audit --no-fund
npm run build

echo
echo "Done. Now restart the services:"
echo "  sudo systemctl restart lkms-web lkms-whatsapp-sender"
