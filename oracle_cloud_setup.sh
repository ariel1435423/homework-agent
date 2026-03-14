#!/bin/bash
# oracle_cloud_setup.sh
# הפעל על Ubuntu VM ב-Oracle Cloud Free Tier
# sudo bash oracle_cloud_setup.sh

set -e
export DEBIAN_FRONTEND=noninteractive   # מונע שאלות אינטראקטיביות
echo "=== Homework Agent – Oracle Cloud Setup ==="

# --- 1. עדכון מערכת + Python בפקודה אחת ---
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq --no-install-recommends \
    python3 python3-pip python3-venv curl unzip ca-certificates gnupg

# --- 2. Docker ---
curl -fsSL https://get.docker.com | sh -s -- --quiet
systemctl enable --now docker

# --- 3. WAHA – מתחיל pull ברקע בזמן שPython מותקן ---
echo "[...] Pulling WAHA image in background..."
docker pull devlikeapro/waha &
WAHA_PULL_PID=$!

# --- 4. תיקיית הפרויקט ---
mkdir -p /opt/homework-agent

# --- 5. venv + packages (מתרחש במקביל ל-docker pull) ---
echo "[...] Installing Python packages..."
cd /opt/homework-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -q --no-cache-dir playwright python-dotenv requests

echo "[...] Installing Playwright + Chromium..."
playwright install-deps chromium
playwright install chromium
echo "[OK] Python packages ready"

# --- 6. המתן ל-WAHA pull לסיים, הפעל container ---
echo "[...] Waiting for WAHA pull to finish..."
wait $WAHA_PULL_PID
docker run -d \
    --name waha \
    --restart always \
    -p 3000:3000 \
    -e WHATSAPP_API_KEY=mysecret \
    -e WHATSAPP_START_SESSION=default \
    devlikeapro/waha
echo "[OK] WAHA running on port 3000"

# --- 7. cron job – כל יומיים בשעה 08:00 ---
CRON_LINE="0 8 */2 * * HEADLESS=true /opt/homework-agent/.venv/bin/python /opt/homework-agent/run_all.py >> /opt/homework-agent/cron.log 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "[OK] Cron job: every 2 days at 08:00"

# --- 8. ניקוי cache ---
apt-get clean && rm -rf /var/lib/apt/lists/*

echo ""
echo "=== DONE ==="
echo ""
echo "Next steps:"
echo "1. Upload files:   scp -r C:/homework-agent/* ubuntu@YOUR_IP:/opt/homework-agent/"
echo "2. Edit .env:      nano /opt/homework-agent/.env"
echo "3. First run:      cd /opt/homework-agent && HEADLESS=true .venv/bin/python run_all.py"
echo "4. Check logs:     tail -f /opt/homework-agent/cron.log"
echo ""
echo "WAHA dashboard: http://YOUR_IP:3000/dashboard  ← scan QR once"
