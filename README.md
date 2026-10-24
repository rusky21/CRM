# Multi-Account Telegram CRM & Telegram Mini App (TMA)

A production-grade, distributed Telegram CRM engine designed to manage multiple Telegram user accounts (MTProto sessions) concurrently through a 1:1 visual & functional **Telegram Mini App (TMA)** replica with an **Admin Alert Bot (`aiogram 3.x`)**.

---

## Architecture Overview

```mermaid
flowchart LR
    Customer["Telegram User"] <-->|MTProto| AccountWorker["Telethon MTProto Pool"]
    AccountWorker -->|xadd| RedisStream["Redis Streams"]
    RedisStream --> IngestionConsumer["Inbound Consumer"]
    IngestionConsumer -->|Upsert| Postgres[("PostgreSQL 16")]
    IngestionConsumer -->|Pub/Sub| AdminBot["Admin Alert Bot"]
    IngestionConsumer -->|Pub/Sub| WSGateway["FastAPI WebSocket"]
    AdminBot -->|Push Alert + Deep Link| AdminTelegram["Admin Mobile"]
    AdminTelegram -->|TMA Deep Link| MiniApp["Telegram Mini App"]
    MiniApp <-->|WebSocket| WSGateway
    WSGateway -->|Dispatch| OutboundDispatcher["Outbound Dispatcher"]
    OutboundDispatcher -->|send_message| AccountWorker
```

---

## 1. Quickstart & Environment Setup

### 1.1 Configure Environment Variables
Copy `backend/.env.example` to `.env`:
```bash
cp backend/.env.example .env
```

Edit `.env` with your production secrets:
```env
# AES-256-GCM 32-byte Encryption Key (Generate via: openssl rand -hex 32)
SECRET_ENCRYPTION_KEY="0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"

# Telegram Client Fallback App Credentials (from https://my.telegram.org)
DEFAULT_TELEGRAM_API_ID=1234567
DEFAULT_TELEGRAM_API_HASH="your_telegram_api_hash_here"

# Admin Alert Bot Credentials (from @BotFather)
ADMIN_BOT_TOKEN="123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
ADMIN_CHAT_ID=987654321

# Mini App Configuration
TMA_BOT_USERNAME="YourAdminBot"
TMA_APP_SHORT_NAME="app"

# Database & Redis URLs
DATABASE_URL="postgresql+asyncpg://postgres:postgres@postgres:5432/tg_crm"
REDIS_URL="redis://redis:6379/0"
```

---

## 2. Launching the Production Stack (Docker Compose)

Launch the entire stack with a single command:
```bash
docker-compose up --build -d
```

### Services Started:
| Service | Container Name | Port | Description |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | `tg_crm_postgres` | `5432` | Relational storage for accounts, dialogues, messages, proxies. |
| **Redis** | `tg_crm_redis` | `6379` | Inbound event streams (`stream:inbound_events`) and Pub/Sub fanout. |
| **Backend** | `tg_crm_backend` | `8000` | FastAPI REST API, WebSocket gateway, MTProto connection pool. |
| **Admin Bot** | `tg_crm_admin_bot` | - | `aiogram 3.x` push notification daemon with TMA deep-linking. |
| **Nginx** | `tg_crm_nginx` | `80`, `443` | Reverse proxy with SSL termination and WebSocket `Upgrade` headers. |

---

## 3. Registering Telegram Accounts

Accounts can be ingested into the pool either via existing `StringSession` strings or interactively.

### Option A: Via Python CLI / Script
```python
from backend.app.db.session import async_session_factory
from backend.app.models.account import Account, AccountStatus
from backend.app.core.security import encrypt_session_string
from backend.app.core.config import settings

async def add_account():
    async with async_session_factory() as session:
        # Encrypt the raw Telethon string session with AES-256-GCM
        raw_session = "1ApWapzMBu3...YourTelethonStringSession..."
        encrypted = encrypt_session_string(raw_session, settings.SECRET_ENCRYPTION_KEY)

        acc = Account(
            phone="+12025550199",
            title="Sales Session #1",
            status=AccountStatus.ACTIVE,
            encrypted_session=encrypted,
            device_fingerprint={"device_model": "iPhone 15 Pro", "app_version": "10.14.1"}
        )
        session.add(acc)
        await session.commit()
```

---

## 4. Configuring the Telegram Mini App in @BotFather

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. Send `/newapp` and select your bot (`@YourAdminBot`).
3. **Title:** `StudioCRM Workspace`
4. **Description:** `Multi-Account Telegram Customer Relationship Management`
5. **Short Name:** Set to `app` (or your configured `TMA_APP_SHORT_NAME`).
6. **Web App URL:** Enter your deployed HTTPS URL:  
   `https://your-domain.com/app/preview.html` (or `https://your-domain.com/app/`).
7. BotFather will provide your direct launch link:  
   `https://t.me/YourAdminBot/app`

---

## 5. End-to-End Operational Walkthrough

1. **Incoming Message:**  
   A client sends a Telegram message to one of your connected accounts (`+12025550199`).
2. **Instant MTProto Catch & Stream Ingestion:**  
   Telethon catches `events.NewMessage` $\rightarrow$ pushes to Redis Stream `stream:inbound_events`.
3. **Database Upsert & Notification:**  
   Consumer upserts the conversation thread in Postgres (increments `unread_count`) and publishes an alert to `channel:admin_alerts`.
4. **Admin Mobile Push:**  
   Admin Bot immediately alerts you:
   ```text
   📩 Новое входящее сообщение!

   👤 Аккаунт: Sales Session #1 (+12025550199)
   💬 От: Dmitry Sokolov (@dmitry_medicus) [ID: 101]
   📝 Текст: «Can we schedule a call regarding the audit?»
   ```
   **Button:** `[💬 Ответить в Mini App]`
5. **Instant Chat Opening:**  
   Tapping the button launches the Mini App inside Telegram, automatically navigates to that account, and opens the chat feed.
6. **Replying via TMA:**  
   Admin types a response and hits Send $\rightarrow$ Transmitted via WebSocket Gateway $\rightarrow$ Outbound Dispatcher $\rightarrow$ Sent through MTProto to the customer with optimistic double checkmarks (`✓✓`).

---

## 6. Circuit Breakers & Proxy Resilience

* **Automatic FloodWait Cooldown:** If Telegram issues a rate-limit (`FloodWaitError`), the account is placed on an automatic cooldown (`FLOOD_WAIT`) and automatically unlocked when the timer expires without crashing the daemon.
* **Proxy Hot-Swapping:** The background `ProxyFailoverMonitor` continuously measures SOCKS5/HTTP socket latencies. If a proxy fails 3 consecutive health checks, affected accounts are hot-swapped to an active backup proxy without terminating user sessions.
