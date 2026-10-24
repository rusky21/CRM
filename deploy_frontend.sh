#!/usr/bin/env bash
# ==============================================================================
# StudioCRM: Server 1 (Frontend & Telegram Mini App Web Hosting)
# Automated Deployment Script for Ubuntu 24.04 LTS (Nginx Multi-Site & Custom SSL)
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
echo "    StudioCRM: Server 1 Frontend Deployment (Multi-Site & Custom SSL)          "
echo "                      Ubuntu 24.04 LTS • Non-Destructive                        "
echo "================================================================================"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# STEP 1: PRIVILEGE & OS VERIFICATION
# ------------------------------------------------------------------------------
echo -e "${BLUE}[1/5] Verifying environment and existing Nginx sites...${NC}"

if [ "${EUID}" -ne 0 ]; then
    echo -e "${RED}[ERROR] This deployment script must be run as root or with sudo.${NC}"
    echo -e "Please execute: ${BOLD}sudo bash deploy_frontend.sh${NC}"
    exit 1
fi

if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    if [[ "${ID}" != "ubuntu" ]] || [[ "${VERSION_ID}" != "24.04" ]]; then
        echo -e "${YELLOW}[WARNING] System is ${PRETTY_NAME:-unknown}. Script is tested for Ubuntu 24.04 LTS.${NC}"
    else
        echo -e "${GREEN}[OK] Operating System confirmed: ${PRETTY_NAME}${NC}"
    fi
fi

# Detect existing sites in Nginx to ensure 100% non-destructive coexistence
if [ -d "/etc/nginx/sites-enabled" ]; then
    EXISTING_SITES=$(ls -1 /etc/nginx/sites-enabled/ 2>/dev/null || true)
    if [ -n "${EXISTING_SITES}" ]; then
        echo -e "${YELLOW}[INFO] Detected existing hosted sites in Nginx:${NC}"
        echo -e "${CYAN}${EXISTING_SITES}${NC}"
        echo -e "${GREEN}--> StudioCRM will be installed alongside your existing sites without touching them!${NC}"
    fi
fi

# ------------------------------------------------------------------------------
# STEP 2: INSTALL CORE DEPENDENCIES (WITHOUT BREAKING RUNNING SITES)
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[2/5] Checking and installing Nginx utilities...${NC}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    git \
    nginx \
    ufw \
    ca-certificates \
    sed

systemctl enable nginx
echo -e "${GREEN}[OK] Nginx is ready.${NC}"

# ------------------------------------------------------------------------------
# STEP 3: INTERACTIVE DOMAIN, BACKEND & SSL WIZARD
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[3/5] Interactive Configuration (Multi-Site & SSL)...${NC}"

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

# Domain Configuration
echo -e "${CYAN}--- 1. Domain Configuration ---${NC}"
echo -e "Enter the specific domain or subdomain for StudioCRM Mini App (e.g. ${BOLD}crm.domain.com${NC} or ${BOLD}domain.com${NC}):"
prompt_var "• Domain for Mini App" "${DETECTED_SERVER1_IP}" FRONTEND_DOMAIN
while [ -z "${FRONTEND_DOMAIN}" ]; do
    echo -e "${RED}[!] Domain or IP is required.${NC}"
    prompt_var "  Please enter domain or IP" "${DETECTED_SERVER1_IP}" FRONTEND_DOMAIN
done

# Port Configuration
DEFAULT_HTTP_PORT="80"
if ss -tulpn 2>/dev/null | grep -q ':80 '; then
    echo -e "${YELLOW}[INFO] Port 80 is already occupied by another service on this server.${NC}"
    DEFAULT_HTTP_PORT="8080"
fi
prompt_var "• HTTP Port for StudioCRM" "${DEFAULT_HTTP_PORT}" FRONTEND_PORT

# Server 2 Backend Connection
echo -e "\n${CYAN}--- 2. Server 2 Backend Connection ---${NC}"
prompt_var "• Server 2 Backend API URL (e.g. http://<SERVER2_IP>:8000 or https://api.domain.com)" "http://${DETECTED_SERVER1_IP}:8000" BACKEND_API_URL
while [ -z "${BACKEND_API_URL}" ]; do
    echo -e "${RED}[!] Backend API URL is required.${NC}"
    prompt_var "  Please enter Server 2 URL" "http://${DETECTED_SERVER1_IP}:8000" BACKEND_API_URL
done
BACKEND_API_URL="${BACKEND_API_URL%/}"

# SSL Certificate Mode
echo -e "\n${CYAN}--- 3. SSL / HTTPS Certificate Mode ---${NC}"
echo -e "Choose how SSL certificates are managed for this domain:"
echo -e "  ${BOLD}1${NC}) Use existing / custom SSL certificate files (fullchain.pem & privkey.pem)"
echo -e "  ${BOLD}2${NC}) HTTP only (Port 80) — behind Cloudflare Flexible SSL, Traefik, or reverse proxy"
echo -e "  ${BOLD}3${NC}) Issue a new Let's Encrypt certificate via Certbot for this domain"

read -r -p "$(echo -e "${BOLD}Select option [1/2/3] (default: 1): ${NC}") " SSL_MODE_CHOICE
SSL_MODE_CHOICE="${SSL_MODE_CHOICE:-1}"

SSL_CERT_PATH=""
SSL_KEY_PATH=""

if [ "${SSL_MODE_CHOICE}" = "1" ]; then
    echo -e "\n${CYAN}Provide paths to your existing SSL certificate files:${NC}"
    # Check default common locations
    DEFAULT_CERT="/etc/letsencrypt/live/${FRONTEND_DOMAIN}/fullchain.pem"
    DEFAULT_KEY="/etc/letsencrypt/live/${FRONTEND_DOMAIN}/privkey.pem"
    if [ ! -f "${DEFAULT_CERT}" ]; then
        DEFAULT_CERT="/etc/ssl/certs/${FRONTEND_DOMAIN}.crt"
        DEFAULT_KEY="/etc/ssl/private/${FRONTEND_DOMAIN}.key"
    fi

    prompt_var "• Path to SSL Certificate (fullchain.pem / cert.crt)" "${DEFAULT_CERT}" SSL_CERT_PATH
    prompt_var "• Path to SSL Private Key (privkey.pem / cert.key)" "${DEFAULT_KEY}" SSL_KEY_PATH

    if [ ! -f "${SSL_CERT_PATH}" ] || [ ! -f "${SSL_KEY_PATH}" ]; then
        echo -e "${YELLOW}[WARNING] One or both certificate files were not found on disk right now.${NC}"
        echo -e "Paths specified: ${SSL_CERT_PATH} and ${SSL_KEY_PATH}"
        read -r -p "Proceed with these paths anyway? [Y/n]: " proceed_cert
        if [[ "${proceed_cert}" =~ ^[Nn]$ ]]; then
            echo -e "${YELLOW}Falling back to HTTP (port 80). You can add SSL paths in /etc/nginx/sites-available/studiocrm-tma later.${NC}"
            SSL_MODE_CHOICE="2"
        fi
    fi
elif [ "${SSL_MODE_CHOICE}" = "3" ]; then
    apt-get install -y --no-install-recommends certbot python3-certbot-nginx
    prompt_var "• Email for Let's Encrypt notifications" "admin@${FRONTEND_DOMAIN}" CERTBOT_EMAIL
fi

# ------------------------------------------------------------------------------
# STEP 4: DEPLOY ISOLATED WEB ASSETS & PATCH PREVIEW.HTML
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[4/5] Deploying Web App files to isolated directory...${NC}"

# Use dedicated directory that NEVER conflicts with other sites in /var/www/
WEB_ROOT="/var/www/studiocrm-tma"
mkdir -p "${WEB_ROOT}"

if [ -d "frontend" ]; then
    cp -r frontend/* "${WEB_ROOT}/" 2>/dev/null || true
    if [ -f "frontend/preview.html" ]; then
        cp -f "frontend/preview.html" "${WEB_ROOT}/index.html"
    fi
else
    echo -e "${RED}[ERROR] Directory 'frontend' not found in current folder ($(pwd)).${NC}"
    exit 1
fi

# Inject Backend API URL into preview.html and index.html
echo -e "${CYAN}--> Injecting Server 2 Backend URL (${BACKEND_API_URL}) into Web App...${NC}"
INJECTION="<script>window.__STUDIOCRM_BACKEND_URL__='${BACKEND_API_URL}';</script>"
sed -i "s|<head>|<head>\n  ${INJECTION}|g" "${WEB_ROOT}/preview.html" 2>/dev/null || true
sed -i "s|<head>|<head>\n  ${INJECTION}|g" "${WEB_ROOT}/index.html" 2>/dev/null || true

chown -R www-data:www-data "${WEB_ROOT}"
chmod -R 755 "${WEB_ROOT}"

# ------------------------------------------------------------------------------
# STEP 5: GENERATE DEDICATED NGINX CONFIG & REVERSE PROXY
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[5/5] Generating Nginx Virtual Host and location snippets...${NC}"

# Also generate a reusable location snippet for inclusion into existing server blocks
SNIPPET_DIR="/etc/nginx/snippets"
mkdir -p "${SNIPPET_DIR}"
SNIPPET_CONF="${SNIPPET_DIR}/studiocrm.conf"

cat > "${SNIPPET_CONF}" <<EOF
# ==============================================================================
# StudioCRM Reusable Location Snippet (Include in any existing server block)
# Example: include /etc/nginx/snippets/studiocrm.conf;
# ==============================================================================

# Reverse Proxy for StudioCRM Backend REST & WebSocket Gateway
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
EOF
echo -e "${GREEN}[OK] Location snippet created at ${SNIPPET_CONF}.${NC}"

# Create dedicated virtual host configuration
NGINX_SITE="/etc/nginx/sites-available/studiocrm-tma"

if [ "${SSL_MODE_CHOICE}" = "1" ] && [ -n "${SSL_CERT_PATH}" ] && [ -n "${SSL_KEY_PATH}" ]; then
    # Full HTTPS Server Block with Custom SSL
    cat > "${NGINX_SITE}" <<EOF
# ==============================================================================
# StudioCRM: Dedicated Virtual Host with Custom SSL
# Coexists cleanly with other sites in /etc/nginx/sites-available/
# ==============================================================================

server {
    listen ${FRONTEND_PORT};
    listen [::]:${FRONTEND_PORT};
    server_name ${FRONTEND_DOMAIN};

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${FRONTEND_DOMAIN};

    # Custom SSL Certificates
    ssl_certificate ${SSL_CERT_PATH};
    ssl_certificate_key ${SSL_KEY_PATH};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    root ${WEB_ROOT};
    index preview.html index.html;

    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_types text/plain text/css text/xml application/json application/javascript application/xml+rss application/atom+xml image/svg+xml;

    # Telegram Mini App Security Headers (Frame embedding allowed for Telegram)
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob: wss: ws:; frame-ancestors *;" always;
    add_header Access-Control-Allow-Origin "*" always;

    location / {
        try_files \$uri \$uri/ /preview.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # Include backend reverse proxy snippet
    include ${SNIPPET_CONF};
}
EOF
    FINAL_PROTOCOL="https"

elif [ "${SSL_MODE_CHOICE}" = "3" ]; then
    # Certbot Managed Setup
    cat > "${NGINX_SITE}" <<EOF
server {
    listen ${FRONTEND_PORT};
    listen [::]:${FRONTEND_PORT};
    server_name ${FRONTEND_DOMAIN};

    root ${WEB_ROOT};
    index preview.html index.html;

    gzip on;
    gzip_types text/plain text/css text/xml application/json application/javascript image/svg+xml;

    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob: wss: ws:; frame-ancestors *;" always;
    add_header Access-Control-Allow-Origin "*" always;

    location / {
        try_files \$uri \$uri/ /preview.html;
    }

    include ${SNIPPET_CONF};
}
EOF
    FINAL_PROTOCOL="http"
else
    # HTTP Only / External SSL Offloading
    cat > "${NGINX_SITE}" <<EOF
server {
    listen ${FRONTEND_PORT};
    listen [::]:${FRONTEND_PORT};
    server_name ${FRONTEND_DOMAIN};

    root ${WEB_ROOT};
    index preview.html index.html;

    gzip on;
    gzip_types text/plain text/css text/xml application/json application/javascript image/svg+xml;

    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: blob: wss: ws:; frame-ancestors *;" always;
    add_header Access-Control-Allow-Origin "*" always;

    location / {
        try_files \$uri \$uri/ /preview.html;
    }

    include ${SNIPPET_CONF};
}
EOF
    FINAL_PROTOCOL="http"
fi

# Disable default welcome page if custom port is used so it doesn't conflict with port 80
if [ "${FRONTEND_PORT}" != "80" ] && [ -f /etc/nginx/sites-enabled/default ]; then
    rm -f /etc/nginx/sites-enabled/default
fi

# Enable ONLY the StudioCRM site without touching existing sites
ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/studiocrm-tma

# Test Nginx configuration before reloading
echo -e "${CYAN}--> Testing Nginx configuration integrity (nginx -t)...${NC}"
if nginx -t; then
    if systemctl is-active --quiet nginx; then
        systemctl reload nginx
        echo -e "${GREEN}[OK] Nginx successfully reloaded without affecting other sites.${NC}"
    else
        systemctl restart nginx || systemctl start nginx
        echo -e "${GREEN}[OK] Nginx successfully started and running.${NC}"
    fi
else
    echo -e "${RED}[ERROR] Nginx syntax test failed. Removing link to prevent breaking existing sites.${NC}"
    rm -f /etc/nginx/sites-enabled/studiocrm-tma
    exit 1
fi

# If Certbot was chosen, obtain certificate now
if [ "${SSL_MODE_CHOICE}" = "3" ]; then
    echo -e "${CYAN}--> Running Certbot for ${FRONTEND_DOMAIN}...${NC}"
    if certbot --nginx -d "${FRONTEND_DOMAIN}" --non-interactive --agree-tos -m "${CERTBOT_EMAIL}" --redirect; then
        echo -e "${GREEN}[OK] Certbot SSL configured!${NC}"
        FINAL_PROTOCOL="https"
    else
        echo -e "${YELLOW}[WARNING] Certbot failed. Operating over HTTP on port ${FRONTEND_PORT}.${NC}"
    fi
fi

# Firewall: Ensure standard and custom web ports are open
ufw allow 22/tcp comment 'SSH' > /dev/null 2>&1 || true
ufw allow 80/tcp comment 'HTTP' > /dev/null 2>&1 || true
ufw allow 443/tcp comment 'HTTPS' > /dev/null 2>&1 || true
if [ "${FRONTEND_PORT}" != "80" ] && [ "${FRONTEND_PORT}" != "443" ]; then
    ufw allow "${FRONTEND_PORT}/tcp" comment 'StudioCRM TMA' > /dev/null 2>&1 || true
fi

PORT_SUFFIX=""
if [ "${FRONTEND_PORT}" != "80" ] && [ "${FRONTEND_PORT}" != "443" ]; then
    PORT_SUFFIX=":${FRONTEND_PORT}"
fi

FINAL_URL="${FINAL_PROTOCOL}://${FRONTEND_DOMAIN}${PORT_SUFFIX}/preview.html"

# ------------------------------------------------------------------------------
# FINAL SUMMARY & BOTFATHER INSTRUCTIONS
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}================================================================================"
echo "          🎉 StudioCRM Frontend Deployed Successfully (Multi-Site Active)       "
echo "================================================================================${NC}"

echo -e "\n${BOLD}Telegram Mini App Access:${NC}"
echo -e "   • Public Mini App URL:   ${BOLD}${CYAN}${FINAL_URL}${NC}"
echo -e "   • Backend Routed Target: ${CYAN}${BACKEND_API_URL}${NC}"
echo -e "   • Web Root Directory:    ${CYAN}${WEB_ROOT}${NC}"

echo -e "\n${BOLD}💡 Note for Multi-Site Servers:${NC}"
echo -e "   • All existing Nginx sites were preserved untouched in ${CYAN}/etc/nginx/sites-enabled/${NC}."
echo -e "   • StudioCRM configuration is located at ${CYAN}${NGINX_SITE}${NC}."
echo -e "   • If you wish to route /api/ inside an existing domain instead of a subdomain,"
echo -e "     simply add: ${BOLD}include ${SNIPPET_CONF};${NC} into your existing server block."

echo -e "\n${BOLD}📱 Instructions for @BotFather:${NC}"
echo -e "   1. Open ${CYAN}https://t.me/BotFather${NC} in Telegram"
echo -e "   2. Send ${BOLD}/newapp${NC} and select your bot"
echo -e "   3. When prompted for Web App URL, paste:"
echo -e "      ${BOLD}${CYAN}${FINAL_URL}${NC}"
echo -e "   4. Set short name: ${BOLD}app${NC}"

echo -e "\n${GREEN}Deployment complete at $(date -u +"%Y-%m-%d %H:%M:%SZ").${NC}\n"
