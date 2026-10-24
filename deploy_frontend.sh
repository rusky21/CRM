#!/usr/bin/env bash
# ==============================================================================
# StudioCRM: Server 1 (Frontend & Telegram Mini App Web Hosting)
# Automated Deployment Script for Ubuntu 24.04 LTS (Nginx + Certbot SSL)
# ==============================================================================

set -euo pipefail

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear || true

echo -e "${CYAN}${BOLD}"
echo "================================================================================"
echo "    StudioCRM: Server 1 Deployment Wizard (Mini App Web Hosting & Nginx)       "
echo "                      Ubuntu 24.04 LTS • SSL & Let's Encrypt                    "
echo "================================================================================"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# STEP 1: PRIVILEGE & OS VERIFICATION
# ------------------------------------------------------------------------------
echo -e "${BLUE}[1/5] Verifying root privileges and OS version...${NC}"

if [ "${EUID}" -ne 0 ]; then
    echo -e "${RED}[ERROR] This deployment script must be run as root or with sudo.${NC}"
    echo -e "Please execute: ${BOLD}sudo bash deploy_frontend.sh${NC}"
    exit 1
fi

if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    if [[ "${ID}" != "ubuntu" ]] || [[ "${VERSION_ID}" != "24.04" ]]; then
        echo -e "${YELLOW}[WARNING] System is ${PRETTY_NAME:-unknown}. Optimized for Ubuntu 24.04 LTS.${NC}"
    else
        echo -e "${GREEN}[OK] Operating System confirmed: ${PRETTY_NAME}${NC}"
    fi
fi

# ------------------------------------------------------------------------------
# STEP 2: INSTALL NGINX, CERTBOT & CORE UTILITIES
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[2/5] Installing Nginx, Certbot and networking tools...${NC}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw \
    ca-certificates \
    sed

systemctl enable nginx
echo -e "${GREEN}[OK] Nginx and Certbot installed.${NC}"

# ------------------------------------------------------------------------------
# STEP 3: INTERACTIVE DOMAIN & BACKEND API WIZARD
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[3/5] Interactive Frontend Configuration...${NC}"

prompt_var() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    local input=""
    if [ -n "${default}" ]; then
        read -r -p "$(echo -e "${BOLD}${prompt}${NC} [default: ${CYAN}${default}${NC}]: ") " input
    else
        read -r -p "$(echo -e "${BOLD}${prompt}${NC}: ") " input
    fi

    if [ -z "${input}" ]; then
        eval "${var_name}='${default}'"
    else
        eval "${var_name}='${input}'"
    fi
}

DETECTED_SERVER1_IP=$(curl -s -4 ifconfig.me || curl -s -4 api.ipify.org || echo "127.0.0.1")

echo -e "${CYAN}--- Server 1 Domain Configuration ---${NC}"
prompt_var "• Domain name for Mini App (e.g. crm.myagency.com or public IP)" "${DETECTED_SERVER1_IP}" FRONTEND_DOMAIN
while [ -z "${FRONTEND_DOMAIN}" ]; do
    echo -e "${RED}[!] Domain or IP is required.${NC}"
    prompt_var "  Please enter domain or IP" "${DETECTED_SERVER1_IP}" FRONTEND_DOMAIN
done

echo -e "\n${CYAN}--- Server 2 Backend Connection ---${NC}"
prompt_var "• Server 2 Backend API URL (e.g. http://1.2.3.4:8000 or https://api.myagency.com)" "http://${DETECTED_SERVER1_IP}:8000" BACKEND_API_URL
while [ -z "${BACKEND_API_URL}" ]; do
    echo -e "${RED}[!] Backend API URL is required to route Telegram requests.${NC}"
    prompt_var "  Please enter Server 2 URL" "http://${DETECTED_SERVER1_IP}:8000" BACKEND_API_URL
done

# Strip trailing slashes
BACKEND_API_URL="${BACKEND_API_URL%/}"

prompt_var "• Email for Let's Encrypt SSL notifications" "admin@${FRONTEND_DOMAIN}" CERTBOT_EMAIL

# ------------------------------------------------------------------------------
# STEP 4: DEPLOY WEB ASSETS & PATCH PREVIEW.HTML
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[4/5] Deploying Web App files and configuring Nginx reverse proxy...${NC}"

WEB_ROOT="/var/www/telegram-crm"
mkdir -p "${WEB_ROOT}"

# Copy frontend source files
if [ -d "frontend" ]; then
    cp -r frontend/* "${WEB_ROOT}/" 2>/dev/null || true
    if [ -f "frontend/preview.html" ]; then
        cp -f "frontend/preview.html" "${WEB_ROOT}/index.html"
    fi
else
    echo -e "${RED}[ERROR] Directory 'frontend' not found in current folder ($(pwd)).${NC}"
    echo -e "Please run this script from the project root repository directory."
    exit 1
fi

# Ensure preview.html is patched with Backend Bridge injection
echo -e "${CYAN}--> Injecting Server 2 Backend Bridge configuration into Web App...${NC}"
INJECTION="<script>window.__STUDIOCRM_BACKEND_URL__='${BACKEND_API_URL}';</script>"
sed -i "s|<head>|<head>\n  ${INJECTION}|g" "${WEB_ROOT}/preview.html" 2>/dev/null || true
sed -i "s|<head>|<head>\n  ${INJECTION}|g" "${WEB_ROOT}/index.html" 2>/dev/null || true

chown -R www-data:www-data "${WEB_ROOT}"
chmod -R 755 "${WEB_ROOT}"

# Configure Nginx Site Block
NGINX_CONF="/etc/nginx/sites-available/telegram-crm"

cat > "${NGINX_CONF}" <<EOF
# ==============================================================================
# StudioCRM: Server 1 Frontend & TMA Web Server Configuration
# ==============================================================================

server {
    listen 80;
    listen [::]:80;
    server_name ${FRONTEND_DOMAIN};

    root ${WEB_ROOT};
    index preview.html index.html;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;

    # Telegram Mini App Security Headers (ALLOW IFRAME EMBEDDING IN TELEGRAM CLIENTS)
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob: wss: ws:; frame-ancestors *;" always;
    add_header Access-Control-Allow-Origin "*" always;

    # Static Web App files
    location / {
        try_files \$uri \$uri/ /preview.html;
    }

    # Static Assets Cache
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Secure Reverse Proxy to Server 2 (Backend REST & WebSocket Gateway)
    # Eliminates Mixed-Content and Cross-Origin blocking inside Telegram WebViews
    location /api/ {
        proxy_pass ${BACKEND_API_URL}/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        proxy_buffering off;
    }
}
EOF

# Enable Site and Disable Default
ln -sf "${NGINX_CONF}" /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
nginx -t
systemctl reload nginx
echo -e "${GREEN}[OK] Nginx site configured and active.${NC}"

# Configure UFW Firewall
ufw allow 22/tcp comment 'SSH Access' > /dev/null
ufw allow 80/tcp comment 'HTTP Web / TMA' > /dev/null
ufw allow 443/tcp comment 'HTTPS Web / TMA' > /dev/null
echo "y" | ufw enable > /dev/null || true

# ------------------------------------------------------------------------------
# STEP 5: SSL CERTIFICATE ISSUANCE (CERTBOT)
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[5/5] Configuring SSL Certificate with Let's Encrypt...${NC}"

IS_IP=false
if [[ "${FRONTEND_DOMAIN}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    IS_IP=true
fi

if [ "${IS_IP}" = "false" ]; then
    echo -e "${CYAN}--> Requesting SSL certificate for domain: ${FRONTEND_DOMAIN}...${NC}"
    if certbot --nginx -d "${FRONTEND_DOMAIN}" --non-interactive --agree-tos -m "${CERTBOT_EMAIL}" --redirect; then
        echo -e "${GREEN}[OK] HTTPS / SSL Certificate successfully issued and configured!${NC}"
        FINAL_PROTOCOL="https"
    else
        echo -e "${YELLOW}[WARNING] Let's Encrypt issuance failed. Ensure DNS A-record points to ${DETECTED_SERVER1_IP}.${NC}"
        echo -e "You can retry later using: ${BOLD}certbot --nginx -d ${FRONTEND_DOMAIN}${NC}"
        FINAL_PROTOCOL="http"
    fi
else
    echo -e "${YELLOW}[INFO] IP address detected (${FRONTEND_DOMAIN}). Let's Encrypt requires a domain name.${NC}"
    echo -e "Serving Mini App over HTTP on port 80."
    FINAL_PROTOCOL="http"
fi

# ------------------------------------------------------------------------------
# FINAL SUMMARY & BOTFATHER INSTRUCTIONS
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}================================================================================"
echo "          🎉 Server 1 (Frontend & TMA Web App) Deployed Successfully!           "
echo "================================================================================${NC}"

echo -e "\n${BOLD}Telegram Mini App Access:${NC}"
echo -e "   • Web App Direct URL:    ${CYAN}${FINAL_PROTOCOL}://${FRONTEND_DOMAIN}/preview.html${NC}"
echo -e "   • Backend Routed Target: ${CYAN}${BACKEND_API_URL}${NC}"

echo -e "\n${BOLD}📱 Instructions for @BotFather Configuration:${NC}"
echo -e "   1. Open ${CYAN}https://t.me/BotFather${NC} in Telegram"
echo -e "   2. Send ${BOLD}/newapp${NC} and select your bot"
echo -e "   3. When prompted for Web App URL, paste:"
echo -e "      ${BOLD}${CYAN}${FINAL_PROTOCOL}://${FRONTEND_DOMAIN}/preview.html${NC}"
echo -e "   4. Set short name: ${BOLD}app${NC}"
echo -e "   5. Your direct Telegram launch link is ready!"

echo -e "\n${GREEN}Deployment finished at $(date -u +"%Y-%m-%d %H:%M:%SZ").${NC}\n"
