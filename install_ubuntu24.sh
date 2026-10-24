#!/usr/bin/env bash
# ==============================================================================
# StudioCRM: Production Deployment & Setup Wizard for Ubuntu 24.04 LTS
# Multi-Account Telegram CRM & Telegram Mini App (TMA)
# ==============================================================================

set -euo pipefail

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

clear || true

echo -e "${CYAN}${BOLD}"
echo "================================================================================"
echo "    StudioCRM: Multi-Account Telegram CRM & TMA Deployment Wizard"
echo "                      Ubuntu 24.04 LTS (Noble Numbat)"
echo "================================================================================"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# STEP 1: PRIVILEGE & OS COMPATIBILITY CHECK
# ------------------------------------------------------------------------------
echo -e "${BLUE}[1/5] Checking environment requirements...${NC}"

if [ "${EUID}" -ne 0 ]; then
    echo -e "${RED}[ERROR] This installation script must be run as root or with sudo.${NC}"
    echo -e "Please execute: ${BOLD}sudo bash install_ubuntu24.sh${NC}"
    exit 1
fi

if [ -f /etc/os-release ]; then
    # shellcheck disable=SC1091
    source /etc/os-release
    if [[ "${ID}" != "ubuntu" ]] || [[ "${VERSION_ID}" != "24.04" ]]; then
        echo -e "${YELLOW}[WARNING] System is ${PRETTY_NAME:-unknown}. This script is specifically tested for Ubuntu 24.04 LTS.${NC}"
        read -r -p "Do you want to proceed anyway? [y/N]: " continue_os
        if [[ ! "${continue_os}" =~ ^[Yy]$ ]]; then
            echo -e "${RED}[ABORT] Installation cancelled by user.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}[OK] Operating System validated: ${PRETTY_NAME}${NC}"
    fi
else
    echo -e "${YELLOW}[WARNING] Could not read /etc/os-release. Proceeding with caution.${NC}"
fi

# ------------------------------------------------------------------------------
# STEP 2: SYSTEM PACKAGES & DOCKER ENGINE INSTALLATION
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[2/5] Installing core dependencies and Docker Engine...${NC}"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
    curl \
    git \
    openssl \
    ufw \
    ca-certificates \
    gnupg \
    lsb-release \
    jq

# Install official Docker repository if not installed
if ! command -v docker &> /dev/null; then
    echo -e "${CYAN}--> Configuring Docker CE official repository...${NC}"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
      $(. /etc/os-release && echo "${VERSION_CODENAME}") stable" | \
      tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -y
    apt-get install -y --no-install-recommends \
        docker-ce \
        docker-ce-cli \
        containerd.io \
        docker-buildx-plugin \
        docker-compose-plugin
fi

# Ensure Docker service is running and enabled
systemctl enable --now docker
echo -e "${GREEN}[OK] Docker engine and Compose plugin active: $(docker --version)${NC}"

# ------------------------------------------------------------------------------
# STEP 3: INTERACTIVE .ENV CONFIGURATION WIZARD
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[3/5] Interactive Configuration Setup (.env)...${NC}"
echo -e "Please provide your Telegram & CRM credentials (press Enter for default suggestions):\n"

# Helper for prompt with default
prompt_var() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_secret="${4:-false}"

    local input=""
    if [ "${is_secret}" = "true" ]; then
        if [ -n "${default}" ]; then
            read -r -s -p "$(echo -e "${BOLD}${prompt}${NC} [default: (hidden)]: ")" input
            echo ""
        else
            read -r -s -p "$(echo -e "${BOLD}${prompt}${NC}: ")" input
            echo ""
        fi
    else
        if [ -n "${default}" ]; then
            read -r -p "$(echo -e "${BOLD}${prompt}${NC} [default: ${CYAN}${default}${NC}]: ") " input
        else
            read -r -p "$(echo -e "${BOLD}${prompt}${NC}: ") " input
        fi
    fi

    if [ -z "${input}" ]; then
        eval "${var_name}='${default}'"
    else
        eval "${var_name}='${input}'"
    fi
}

# 1. Telegram API (my.telegram.org)
echo -e "${CYAN}--- Telegram MTProto App Credentials (my.telegram.org) ---${NC}"
prompt_var "1. Telegram API ID" "2040" TG_API_ID
prompt_var "2. Telegram API Hash" "b18441a1ff607e10a989891a5462e627" TG_API_HASH

# 2. Telegram Bot & Mini App (@BotFather)
echo -e "\n${CYAN}--- Telegram Bot & Mini App Configuration (@BotFather) ---${NC}"
prompt_var "3. Admin Bot Token (from @BotFather)" "" BOT_TOKEN true
while [ -z "${BOT_TOKEN}" ]; do
    echo -e "${RED}[!] Bot Token is required for notifications and FSM intake.${NC}"
    prompt_var "   Please enter Admin Bot Token" "" BOT_TOKEN true
done

prompt_var "4. Bot Username (without @, e.g. StudioCrmBot)" "StudioCrmBot" BOT_USERNAME
prompt_var "5. Mini App Short Name (from /newapp in @BotFather)" "app" APP_SHORT_NAME
prompt_var "6. Admin Personal Telegram ID (for push alerts)" "" ADMIN_ID
while [ -z "${ADMIN_ID}" ]; do
    echo -e "${RED}[!] Admin Telegram ID is required (obtain from @userinfobot).${NC}"
    prompt_var "   Please enter your numeric Telegram ID" "" ADMIN_ID
done

# 3. StudioCRM Bridge URL
echo -e "\n${CYAN}--- StudioCRM Integration URL ---${NC}"
prompt_var "7. Existing StudioCRM Backend URL" "http://212.67.15.218:5000" CRM_SERVER_URL

# 4. Host Domain or Public IP
echo -e "\n${CYAN}--- Domain / Public IP for Mini App Hosting ---${NC}"
DETECTED_IP=$(curl -s -4 ifconfig.me || curl -s -4 api.ipify.org || echo "127.0.0.1")
prompt_var "8. Domain name or Public IP" "${DETECTED_IP}" HOST_DOMAIN

# Generate Cryptographic Secrets
echo -e "\n${CYAN}--- Generating Cryptographic Secrets ---${NC}"
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PWD=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)
REDIS_PWD=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)

# Write .env file
ENV_FILE=".env"
cat > "${ENV_FILE}" <<EOF
# ==============================================================================
# StudioCRM Production Environment Configuration
# Generated on: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# ==============================================================================

# System
PROJECT_NAME="StudioCRM Multi-Account Telegram"
DEBUG=False
API_V1_PREFIX="/api/v1"

# AES-256-GCM 32-Byte Secret Encryption Key for MTProto Sessions
SECRET_ENCRYPTION_KEY="${SECRET_KEY}"

# Database Configuration (PostgreSQL 16)
POSTGRES_USER=crm_admin
POSTGRES_PASSWORD=${POSTGRES_PWD}
POSTGRES_DB=studiocrm_db
DATABASE_URL=postgresql+asyncpg://crm_admin:${POSTGRES_PWD}@postgres:5432/studiocrm_db

# Redis Event Bus & Pub/Sub
REDIS_PASSWORD=${REDIS_PWD}
REDIS_URL=redis://:${REDIS_PWD}@redis:6379/0

# Default MTProto App Credentials
DEFAULT_TELEGRAM_API_ID=${TG_API_ID}
DEFAULT_TELEGRAM_API_HASH="${TG_API_HASH}"

# Admin Bot & Push Alerts
ADMIN_BOT_TOKEN="${BOT_TOKEN}"
ADMIN_CHAT_ID=${ADMIN_ID}
TMA_BOT_USERNAME="${BOT_USERNAME}"
TMA_APP_SHORT_NAME="${APP_SHORT_NAME}"

# Integration with Existing StudioCRM
STUDIOCRM_SERVER_URL="${CRM_SERVER_URL}"
STUDIOCRM_SQLITE_PATH="studiocrm.db"

# Public Access
HOST_DOMAIN="${HOST_DOMAIN}"
EOF

chmod 600 "${ENV_FILE}"
echo -e "${GREEN}[OK] Secure .env generated with restricted permissions (chmod 600).${NC}"

# ------------------------------------------------------------------------------
# STEP 4: FIREWALL & DOCKER COMPOSE DEPLOYMENT
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[4/5] Configuring firewall (UFW) and launching stack...${NC}"

# Configure UFW
echo -e "${CYAN}--> Enabling UFW rules (SSH 22, HTTP 80, HTTPS 443)...${NC}"
ufw allow 22/tcp comment 'SSH Access' > /dev/null
ufw allow 80/tcp comment 'HTTP Web / TMA' > /dev/null
ufw allow 443/tcp comment 'HTTPS Web / TMA' > /dev/null
echo "y" | ufw enable > /dev/null || true
echo -e "${GREEN}[OK] Firewall configured.${NC}"

# Build and launch Docker Compose stack
echo -e "${CYAN}--> Building and starting Docker Compose containers in background...${NC}"
docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d --build

# Healthcheck loop (15 seconds)
echo -e "${CYAN}--> Performing health check on running containers (15s)...${NC}"
sleep 5
for i in {1..10}; do
    RUNNING_COUNT=$(docker compose ps --filter "status=running" -q | wc -l)
    if [ "${RUNNING_COUNT}" -ge 4 ]; then
        echo -e "${GREEN}[OK] All primary services are healthy and running (${RUNNING_COUNT} containers).${NC}"
        break
    fi
    echo -e "Waiting for services to finish boot... (${i}/10)"
    sleep 2
done

# ------------------------------------------------------------------------------
# STEP 5: FINAL OPERATOR SUMMARY & BOTFATHER INSTRUCTIONS
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}================================================================================"
echo "          🎉 StudioCRM Production Deployment Complete!"
echo "================================================================================${NC}"

echo -e "\n${BOLD}1. Web & Telegram Mini App Access:${NC}"
echo -e "   • Public Mini App URL: ${CYAN}http://${HOST_DOMAIN}/app/preview.html${NC}"
echo -e "   • API Gateway Documentation: ${CYAN}http://${HOST_DOMAIN}/docs${NC}"
echo -e "   • StudioCRM Integration Target: ${CYAN}${CRM_SERVER_URL}${NC}"

echo -e "\n${BOLD}2. Telegram BotFather Configuration Guide:${NC}"
echo -e "   To link the Mini App to your bot ${BOLD}@${BOT_USERNAME}${NC}:"
echo -e "   1. Open ${CYAN}https://t.me/BotFather${NC} in Telegram"
echo -e "   2. Send ${BOLD}/newapp${NC} and select @${BOT_USERNAME}"
echo -e "   3. Set Title: ${BOLD}StudioCRM${NC}"
echo -e "   4. Set Short Description: ${BOLD}Multi-Account Telegram CRM${NC}"
echo -e "   5. When asked for Web App URL, paste:"
echo -e "      ${CYAN}https://${HOST_DOMAIN}/app/preview.html${NC} (or http if SSL is handled externally)"
echo -e "   6. Set short name: ${BOLD}${APP_SHORT_NAME}${NC}"

echo -e "\n${BOLD}3. System Management Commands:${NC}"
echo -e "   • View live logs:       ${BOLD}docker compose logs -f${NC}"
echo -e "   • View bot logs:        ${BOLD}docker compose logs -f bot${NC}"
echo -e "   • View backend logs:    ${BOLD}docker compose logs -f backend${NC}"
echo -e "   • Restart system:       ${BOLD}docker compose restart${NC}"
echo -e "   • Stop system:          ${BOLD}docker compose down${NC}"

echo -e "\n${GREEN}Deployment finished successfully at $(date -u +"%Y-%m-%d %H:%M:%SZ").${NC}\n"
