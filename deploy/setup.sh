#!/bin/bash
# Deployment script for actuva.flamen.es
# Run as root or with sudo on a server with existing nginx sites
set -e

APP_DIR=/opt/actuva
REPO=git@github-actuva:rodioniurev/amnesio.git

echo "=== 1. Clone repo ==="
if [ -d "$APP_DIR" ]; then
    echo "Directory exists, pulling latest..."
    cd $APP_DIR && git pull
else
    git clone $REPO $APP_DIR
fi
cd $APP_DIR

echo "=== 2. Python venv ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== 3. Environment ==="
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo "!!! IMPORTANT: Edit /opt/actuva/.env before continuing !!!"
    echo "    nano /opt/actuva/.env"
    echo "    Then re-run this script."
    echo ""
    exit 1
fi

echo "=== 4. Django setup ==="
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py seed_assistants

echo "=== 5. Create admin user ==="
python manage.py createsuperuser --username admin --email admin@actuva.es || true

echo "=== 6. Set permissions ==="
chown -R www-data:www-data $APP_DIR
chmod -R 755 $APP_DIR

echo "=== 7. Systemd service ==="
cp deploy/actuva.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable actuva
systemctl restart actuva
echo "Gunicorn started on 127.0.0.1:8000"

echo "=== 8. Nginx (alongside existing sites) ==="
cp deploy/nginx-actuva.conf /etc/nginx/sites-available/actuva
ln -sf /etc/nginx/sites-available/actuva /etc/nginx/sites-enabled/
echo "Testing nginx config..."
nginx -t && systemctl reload nginx
echo "Nginx reloaded (other sites unaffected)"

echo "=== 9. SSL (Let's Encrypt) ==="
echo "Run manually after DNS is pointed:"
echo "  certbot --nginx -d actuva.flamen.es"
echo ""

echo "=== DONE ==="
echo "HTTP:  http://actuva.flamen.es"
echo "Admin: http://actuva.flamen.es/admin/"
echo ""
echo "After certbot:"
echo "HTTPS: https://actuva.flamen.es"
