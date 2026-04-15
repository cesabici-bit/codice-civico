#!/usr/bin/env bash
# ==============================================================================
# Codice Civico — VPS Deploy Script (Ubuntu 24.04)
#
# Run as root on a fresh Ubuntu 24.04 VPS (Hetzner CX22 or larger):
#   curl -fsSL https://raw.githubusercontent.com/cesabici-bit/codice-civico/master/scripts/deploy-vps.sh | bash
#
# Or clone first, then:
#   sudo bash scripts/deploy-vps.sh
# ==============================================================================
set -euo pipefail

REPO_URL="https://github.com/cesabici-bit/codice-civico.git"
REPO_DIR="/opt/codice-civico"

echo "============================================================"
echo " Codice Civico — VPS Setup"
echo "============================================================"

# --- 1. System updates ---
echo "=== 1/9 System updates ==="
apt-get update -qq && apt-get upgrade -y -qq

# --- 2. Install Docker ---
echo "=== 2/9 Install Docker ==="
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    echo "Docker installed."
else
    echo "Docker already installed."
fi

# --- 3. Firewall (ufw) ---
echo "=== 3/9 Firewall setup ==="
apt-get install -y -qq ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
echo "Firewall configured (SSH + HTTP + HTTPS)."

# --- 4. fail2ban ---
echo "=== 4/9 fail2ban ==="
apt-get install -y -qq fail2ban
systemctl enable fail2ban
systemctl start fail2ban
echo "fail2ban active."

# --- 5. Clone or update repo ---
echo "=== 5/9 Repository ==="
if [ ! -d "$REPO_DIR" ]; then
    git clone "$REPO_URL" "$REPO_DIR"
    echo "Cloned to $REPO_DIR."
else
    cd "$REPO_DIR" && git pull --ff-only
    echo "Updated $REPO_DIR."
fi

# --- 6. Environment file ---
echo "=== 6/9 Environment ==="
if [ ! -f "$REPO_DIR/.env" ]; then
    cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
    echo ""
    echo "!!! IMPORTANT !!!"
    echo "Edit $REPO_DIR/.env with real passwords, then re-run this script."
    echo "  nano $REPO_DIR/.env"
    echo ""
    exit 1
else
    echo ".env exists."
fi

# --- 7. Build and start ---
echo "=== 7/9 Build & Start ==="
cd "$REPO_DIR"
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
for i in $(seq 1 30); do
    if docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U codicecivico -q 2>/dev/null; then
        echo "PostgreSQL ready."
        break
    fi
    sleep 2
done

# --- 8. Run migrations ---
echo "=== 8/9 Database migrations ==="
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
echo "Migrations applied."

# --- 9. Pull Ollama model ---
echo "=== 9/9 Pull Ollama model ==="
echo "This may take 10-20 minutes on first run..."
docker compose -f docker-compose.prod.yml exec -T ollama \
    ollama pull llama3.1 || \
    echo "WARNING: Ollama model pull failed. Translation will use fallback mode."

# --- Setup backup cron ---
CRON_LINE="0 5 * * * $REPO_DIR/scripts/backup-pg.sh >> /var/log/cc-backup.log 2>&1"
(crontab -l 2>/dev/null | grep -v "backup-pg.sh"; echo "$CRON_LINE") | crontab -
echo "Backup cron set (daily 05:00 UTC)."

# --- Done ---
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "============================================================"
echo " DEPLOY COMPLETE"
echo "============================================================"
echo ""
echo " Frontend:  http://$SERVER_IP/"
echo " API:       http://$SERVER_IP/api/v1/health"
echo " API docs:  http://$SERVER_IP/api/v1/docs"
echo ""
echo " Next step — run initial data ingest:"
echo "   docker compose -f docker-compose.prod.yml exec backend bash scripts/ingest-full.sh"
echo ""
