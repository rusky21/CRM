#!/usr/bin/env bash
# ==============================================================================
# StudioCRM: Server 2 (Backend, MTProto Pool, PostgreSQL, Redis, Alert Bot)
# Automated Deployment Script for Ubuntu 24.04 LTS (Optimized for 2GB RAM VPS)
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
echo "    StudioCRM: Server 2 Deployment Wizard (Backend, MTProto, DB & Bot)         "
echo "                      Ubuntu 24.04 LTS • 2GB RAM Profile                        "
echo "================================================================================"
echo -e "${NC}"

# ------------------------------------------------------------------------------
# STEP 1: PRIVILEGE & OS VERIFICATION
# ------------------------------------------------------------------------------
echo -e "${BLUE}[1/6] Verifying root privileges and OS version...${NC}"

if [ "${EUID}" -ne 0 ]; then
    echo -e "${RED}[ERROR] This deployment script must be run as root or with sudo.${NC}"
    echo -e "Please execute: ${BOLD}sudo bash deploy_backend.sh${NC}"
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
# STEP 2: 2GB RAM SAFEGUARD & SWAPFILE CREATION
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[2/6] Evaluating memory and configuring 2GB Swapfile safeguard...${NC}"

TOTAL_RAM_MB=$(free -m | awk '/^Mem:/ {print $2}')
CURRENT_SWAP_MB=$(free -m | awk '/^Swap:/ {print $2}')

echo -e "Physical RAM detected: ${CYAN}${TOTAL_RAM_MB} MB${NC}"
echo -e "Existing Swap space:   ${CYAN}${CURRENT_SWAP_MB} MB${NC}"

if [ "${CURRENT_SWAP_MB}" -lt 2000 ]; then
    echo -e "${YELLOW}--> Swap is under 2GB. Creating a 2GB swapfile at /swapfile to prevent OOM errors during docker builds...${NC}"
    if [ ! -f /swapfile ]; then
        fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        if ! grep -q "/swapfile" /etc/fstab; then
            echo "/swapfile none swap sw 0 0" >> /etc/fstab
        fi
        # Optimize swappiness for 2GB VPS
        sysctl vm.swappiness=10 > /dev/null 2>&1 || true
        if ! grep -q "vm.swappiness" /etc/sysctl.conf 2>/dev/null; then
            echo "vm.swappiness=10" >> /etc/sysctl.conf
        fi
        echo -e "${GREEN}[OK] 2GB Swapfile successfully active and persisted in /etc/fstab.${NC}"
    else
        swapon /swapfile 2>/dev/null || true
        echo -e "${GREEN}[OK] /swapfile already present; enabled.${NC}"
    fi
else
    echo -e "${GREEN}[OK] Sufficient swap space available (${CURRENT_SWAP_MB} MB).${NC}"
fi

# ------------------------------------------------------------------------------
# STEP 3: SYSTEM PACKAGES & DOCKER ENGINE INSTALLATION
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[3/6] Installing dependencies and Docker Engine...${NC}"

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

if ! command -v docker &> /dev/null; then
    echo -e "${CYAN}--> Setting up official Docker CE repository...${NC}"
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

systemctl enable --now docker
echo -e "${GREEN}[OK] Docker active: $(docker --version)${NC}"

# ------------------------------------------------------------------------------
# STEP 4: INTERACTIVE .ENV CONFIGURATION WIZARD
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[4/6] Interactive Environment Setup (.env)...${NC}"
echo -e "Enter Telegram & CRM parameters for Server 2 (press Enter to accept defaults):\n"

prompt_var() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"
    local is_secret="${4:-false}"

    local input=""
    if [ "${is_secret}" = "true" ]; then
        read -r -s -p "$(echo -e "${BOLD}${prompt}${NC} [default: (hidden)]: ")" input
        echo ""
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

# 1. Telegram App Credentials
echo -e "${CYAN}--- 1. Telegram MTProto Client Credentials (my.telegram.org) ---${NC}"
prompt_var "• Telegram API ID" "2040" TG_API_ID
prompt_var "• Telegram API Hash" "b18441a1ff607e10a989891a5462e627" TG_API_HASH

# 2. Telegram Bot Configuration
echo -e "\n${CYAN}--- 2. Telegram Alert & Intake Bot Configuration (@BotFather) ---${NC}"
prompt_var "• Admin Bot Token" "" BOT_TOKEN true
while [ -z "${BOT_TOKEN}" ]; do
    echo -e "${RED}[!] Bot Token is mandatory for alerts and /new_client FSM.${NC}"
    prompt_var "  Please enter Admin Bot Token" "" BOT_TOKEN true
done

prompt_var "• Admin Bot Username (without @, e.g. StudioCrmBot)" "StudioCrmBot" BOT_USERNAME
prompt_var "• Mini App Short Name (from /newapp)" "app" APP_SHORT_NAME
prompt_var "• Admin Personal Telegram ID (numeric, from @userinfobot)" "" ADMIN_ID
while [ -z "${ADMIN_ID}" ]; do
    echo -e "${RED}[!] Admin Telegram ID is required for push notifications.${NC}"
    prompt_var "  Please enter your numeric Telegram ID" "" ADMIN_ID
done

# 3. StudioCRM Integration & Server 1 CORS
echo -e "\n${CYAN}--- 3. StudioCRM & Server 1 CORS Configuration ---${NC}"
prompt_var "• Existing StudioCRM Backend URL" "http://212.67.15.218:5000" CRM_SERVER_URL
prompt_var "• Server 1 Frontend Domain (for strict CORS, e.g. crm.example.com or *)" "*" FRONTEND_ORIGIN

# Generate secrets
echo -e "\n${CYAN}--> Generating cryptographically secure tokens...${NC}"
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PWD=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)
REDIS_PWD=$(openssl rand -base64 18 | tr -dc 'a-zA-Z0-9' | head -c 24)

DETECTED_BACKEND_IP=$(curl -s -4 ifconfig.me || curl -s -4 api.ipify.org || echo "127.0.0.1")

# Write .env
cat > ".env" <<EOF
# ==============================================================================
# StudioCRM: Server 2 Production Configuration
# Auto-generated: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
# ==============================================================================

PROJECT_NAME="StudioCRM Multi-Account Telegram Backend"
DEBUG=False
API_V1_PREFIX="/api/v1"

# 32-Byte Secret Encryption Key for MTProto Session Store (AES-256-GCM)
SECRET_ENCRYPTION_KEY="${SECRET_KEY}"

# Database Configuration (PostgreSQL 16)
POSTGRES_USER=crm_admin
POSTGRES_PASSWORD=${POSTGRES_PWD}
POSTGRES_DB=studiocrm_db
DATABASE_URL=postgresql+asyncpg://crm_admin:${POSTGRES_PWD}@postgres:5432/studiocrm_db

# Redis Event Bus & Pub/Sub
REDIS_PASSWORD=${REDIS_PWD}
REDIS_URL=redis://redis:6379/0

# MTProto Default App Credentials
DEFAULT_TELEGRAM_API_ID=${TG_API_ID}
DEFAULT_TELEGRAM_API_HASH="${TG_API_HASH}"

# Admin Bot Settings
ADMIN_BOT_TOKEN="${BOT_TOKEN}"
ADMIN_CHAT_ID=${ADMIN_ID}
TMA_BOT_USERNAME="${BOT_USERNAME}"
TMA_APP_SHORT_NAME="${APP_SHORT_NAME}"

# Existing StudioCRM Connection
STUDIOCRM_SERVER_URL="${CRM_SERVER_URL}"
STUDIOCRM_SQLITE_PATH="studiocrm.db"

# Server 1 Frontend Allowed Origin (CORS)
FRONTEND_ORIGIN_DOMAIN="${FRONTEND_ORIGIN}"
EOF

chmod 600 ".env"
echo -e "${GREEN}[OK] .env file saved with secure permissions (chmod 600).${NC}"

# ------------------------------------------------------------------------------
# STEP 5: FIREWALL (UFW) & DOCKER COMPOSE LAUNCH
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}[5/6] Configuring firewall rules and starting backend stack...${NC}"

ufw allow 22/tcp comment 'SSH Access' > /dev/null
ufw allow 8000/tcp comment 'StudioCRM FastAPI & WebSocket' > /dev/null
ufw allow 80/tcp comment 'HTTP' > /dev/null || true
ufw allow 443/tcp comment 'HTTPS' > /dev/null || true
echo "y" | ufw enable > /dev/null || true
echo -e "${GREEN}[OK] Firewall updated: Ports 22 and 8000 open.${NC}"

# Launch docker compose backend profile
echo -e "${CYAN}--> Building and starting Docker containers (postgres, redis, backend, bot)...${NC}"
docker compose -f docker-compose.backend.yml down --remove-orphans 2>/dev/null || true
docker compose -f docker-compose.backend.yml up -d --build

# Health check
echo -e "${CYAN}--> Verifying container health (15 seconds)...${NC}"
sleep 5
for i in {1..10}; do
    RUNNING_SERVICES=$(docker compose -f docker-compose.backend.yml ps --filter "status=running" -q | wc -l)
    if [ "${RUNNING_SERVICES}" -ge 4 ]; then
        echo -e "${GREEN}[OK] All 4 backend services are healthy and running!${NC}"
        break
    fi
    echo -e "Waiting for services to finish boot... (${i}/10)"
    sleep 2
done

# ------------------------------------------------------------------------------
# STEP 6: FINAL CONNECTION SUMMARY FOR SERVER 1
# ------------------------------------------------------------------------------
echo -e "\n${GREEN}${BOLD}================================================================================"
echo "          🎉 Server 2 (Backend Stack) Deployed Successfully!                    "
echo "================================================================================${NC}"

echo -e "\n${BOLD}Backend Access Endpoints:${NC}"
echo -e "   • Public Server 2 IP:      ${CYAN}${DETECTED_BACKEND_IP}${NC}"
echo -e "   • REST API Base URL:       ${CYAN}http://${DETECTED_BACKEND_IP}:8000/api/v1${NC}"
echo -e "   • WebSocket Streaming URL: ${CYAN}ws://${DETECTED_BACKEND_IP}:8000/api/v1/ws${NC}"
echo -e "   • Interactive API Docs:    ${CYAN}http://${DETECTED_BACKEND_IP}:8000/api/v1/docs${NC}"

echo -e "\n${YELLOW}${BOLD}👉 NEXT STEP FOR SERVER 1 (Frontend):${NC}"
echo -e "When running ${BOLD}deploy_frontend.sh${NC} on Server 1, enter:"
echo -e "   BACKEND_API_URL: ${BOLD}${CYAN}http://${DETECTED_BACKEND_IP}:8000${NC}\n"
