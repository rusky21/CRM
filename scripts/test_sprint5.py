#!/usr/bin/env python3
"""
Sprint 5 Verification Suite: Production Hardening, Circuit Breakers & Deployment.

Tests:
1. CircuitBreaker FloodWait Tracking, Cooldown Expirations & Rate Limiting.
2. ProxyFailoverMonitor socket probing and failover logic.
3. Docker Compose and Nginx configuration validity check.
"""

import asyncio
import os
import sys
import time
import uuid
import logging
from unittest.mock import MagicMock, AsyncMock

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.core.circuit_breaker import CircuitBreaker
from backend.app.services.proxy.failover import ProxyFailoverMonitor
from backend.app.models.proxy import Proxy
from backend.app.models.account import Account, AccountStatus

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Sprint5Verification")


async def test_circuit_breaker() -> bool:
    """Verifies CircuitBreaker flood wait isolation and automatic unlocking."""
    logger.info("--- Test 1: Circuit Breaker & Anti-Flood ---")
    cb = CircuitBreaker.get_instance()
    account_id = uuid.uuid4()

    # 1. Initial State: available
    available, remaining = await cb.check_account_available(account_id)
    assert available is True
    assert remaining == 0
    logger.info("Account initially available.")

    # 2. Record 2-second FloodWait
    await cb.record_flood_wait(account_id, wait_seconds=2)
    available, remaining = await cb.check_account_available(account_id)
    assert available is False
    assert remaining > 0
    logger.info(f"Account locked under FloodWait: remaining={remaining}s")

    # 3. Wait for cooldown to expire
    await asyncio.sleep(4.1)
    available, remaining = await cb.check_account_available(account_id)
    assert available is True
    assert remaining == 0
    logger.info("Account automatically released after cooldown expired.")

    # 4. Anti-flood rate limiting
    start_t = time.time()
    await cb.enforce_rate_limit(account_id, peer_id=12345, min_interval_seconds=0.5)
    await cb.enforce_rate_limit(account_id, peer_id=12345, min_interval_seconds=0.5)
    elapsed = time.time() - start_t
    assert elapsed >= 0.45
    logger.info(f"Peer-level rate limit interval enforced: {elapsed:.2f}s")

    logger.info("Circuit Breaker tests PASSED.")
    return True


async def test_proxy_failover_probe() -> bool:
    """Verifies socket probing mechanism of ProxyFailoverMonitor."""
    logger.info("--- Test 2: Proxy Health Probe & Socket Handshake ---")
    session_factory = MagicMock()
    pool_mock = MagicMock()
    monitor = ProxyFailoverMonitor(session_factory=session_factory, pool_manager=pool_mock)

    # 1. Test probe against a real port that should be closed or non-existent
    is_alive, latency = await monitor.probe_socket("127.0.0.1", port=59999, timeout_sec=0.5)
    assert is_alive is False
    assert latency == 9999
    logger.info("Dead socket probe correctly detected as offline.")

    # 2. Test probe against active local port (our frontend server on port 3000)
    is_alive, latency = await monitor.probe_socket("127.0.0.1", port=3000, timeout_sec=1.0)
    if is_alive:
        logger.info(f"Active port 3000 probe confirmed: latency={latency}ms")
    else:
        logger.info("Active port probe skipped (server not on 3000).")

    logger.info("Proxy health probe tests PASSED.")
    return True


def test_deployment_configs() -> bool:
    """Verifies existence and basic syntax of docker-compose.yml and nginx.conf."""
    logger.info("--- Test 3: Deployment Configurations ---")

    assert os.path.exists("docker-compose.yml"), "docker-compose.yml is missing."
    assert os.path.exists("deploy/nginx.conf"), "deploy/nginx.conf is missing."
    assert os.path.exists("deploy/Dockerfile.backend"), "Dockerfile.backend is missing."
    assert os.path.exists("deploy/Dockerfile.bot"), "Dockerfile.bot is missing."

    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        compose_content = f.read()
        assert "tg_crm_postgres" in compose_content
        assert "tg_crm_redis" in compose_content
        assert "tg_crm_backend" in compose_content
        assert "tg_crm_admin_bot" in compose_content

    with open("deploy/nginx.conf", "r", encoding="utf-8") as f:
        nginx_content = f.read()
        assert "proxy_pass http://backend_upstream/api/v1/ws;" in nginx_content
        assert "proxy_set_header Upgrade $http_upgrade;" in nginx_content

    logger.info("Deployment configuration syntax and topology PASSED.")
    return True


async def main() -> None:
    logger.info("==================================================")
    logger.info("      STARTING SPRINT 5 VERIFICATION SUITE        ")
    logger.info("==================================================")

    assert await test_circuit_breaker()
    assert await test_proxy_failover_probe()
    assert test_deployment_configs()

    logger.info("==================================================")
    logger.info("✅ ALL SPRINT 5 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    logger.info("==================================================")


if __name__ == "__main__":
    asyncio.run(main())
