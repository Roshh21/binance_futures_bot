"""
client.py
---------
Binance USDT-M Futures Testnet API wrapper.

Responsibilities:
  - Load API credentials from environment variables (never hard-code secrets).
  - Construct and return a configured `python-binance` Client pointed at the
    Futures Testnet base URL.
  - Provide a lightweight health-check (`ping_exchange`) used at startup.
  - Isolate all Binance client construction so other modules never import
    `python-binance` directly – easier to swap or mock in tests.
"""

from __future__ import annotations

import os
from typing import Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from dotenv import load_dotenv

from src.logging_config import get_logger

logger = get_logger(__name__)

# ── Testnet endpoint ───────────────────────────────────────────────────────────
FUTURES_TESTNET_BASE_URL = "https://testnet.binancefuture.com"

# Env-variable names expected in .env / environment
_ENV_API_KEY    = "BINANCE_TESTNET_API_KEY"
_ENV_API_SECRET = "BINANCE_TESTNET_API_SECRET"


def _load_credentials() -> tuple[str, str]:
    """
    Read API key and secret from the environment (or .env file).

    Raises
    ------
    EnvironmentError
        If either variable is missing or empty.
    """
    load_dotenv()  # silently ignored if .env does not exist

    api_key    = os.getenv(_ENV_API_KEY, "").strip()
    api_secret = os.getenv(_ENV_API_SECRET, "").strip()

    if not api_key:
        raise EnvironmentError(
            f"Missing API key. "
            f"Set {_ENV_API_KEY!r} in your .env file or environment."
        )
    if not api_secret:
        raise EnvironmentError(
            f"Missing API secret. "
            f"Set {_ENV_API_SECRET!r} in your .env file or environment."
        )

    logger.debug("API credentials loaded from environment.")
    return api_key, api_secret


def get_futures_client() -> Client:
    """
    Build and return a `python-binance` Client configured for the
    USDT-M Futures Testnet.

    The client is constructed with:
      - ``testnet=True``  → enables testnet mode inside python-binance
      - Overridden base URL → points every REST call at the testnet endpoint

    Returns
    -------
    binance.client.Client
        Ready-to-use authenticated client.

    Raises
    ------
    EnvironmentError
        If credentials are not found.
    BinanceAPIException / BinanceRequestException
        If the exchange rejects the credentials or is unreachable.
    """
    api_key, api_secret = _load_credentials()

    logger.info("Initialising Binance Futures Testnet client …")

    client = Client(
        api_key=api_key,
        api_secret=api_secret,
        testnet=True,
    )

    # python-binance ≥1.0.19 exposes these constants; override to guarantee
    # every REST call lands on the Futures Testnet host.
    client.FUTURES_URL   = FUTURES_TESTNET_BASE_URL + "/fapi"
    client.API_URL       = FUTURES_TESTNET_BASE_URL          # spot endpoint (unused but consistent)

    logger.debug("Futures base URL set to: %s", client.FUTURES_URL)
    return client


def ping_exchange(client: Client) -> bool:
    """
    Send a lightweight ping to the Futures Testnet to verify connectivity.

    Parameters
    ----------
    client : binance.client.Client
        An already-constructed client from :func:`get_futures_client`.

    Returns
    -------
    bool
        ``True`` if the ping succeeded, ``False`` otherwise.
    """
    try:
        client.futures_ping()
        logger.info("✔ Exchange ping successful – testnet is reachable.")
        return True

    except BinanceAPIException as exc:
        logger.error("Binance API error during ping: [%s] %s", exc.status_code, exc.message)
        return False

    except BinanceRequestException as exc:
        logger.error("Network error during ping: %s", exc)
        return False

    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during ping: %s", exc)
        return False
