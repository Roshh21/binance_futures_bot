"""
orders.py
---------
Order execution logic for the Binance USDT-M Futures Testnet bot.

Provides three public functions – one per supported order type:
  - place_market_order()
  - place_limit_order()
  - place_stop_market_order()   ← bonus Stop-Limit variant

Each function:
  1. Logs the full request payload at DEBUG level (file only).
  2. Calls the Binance API.
  3. Logs the raw response at DEBUG level.
  4. Returns a normalised `OrderResult` dataclass for uniform downstream use.
  5. Raises `OrderError` on any API or network failure so callers can handle
     errors without catching `BinanceAPIException` directly.

A top-level `place_order()` dispatcher routes to the correct function based
on the validated `order_type` string coming from `validators.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException

from src.logging_config import get_logger

logger = get_logger(__name__)


# ── Custom exception ───────────────────────────────────────────────────────────

class OrderError(RuntimeError):
    """
    Raised when an order placement attempt fails.

    Attributes
    ----------
    message   : Human-readable description.
    api_code  : Binance error code (int), or None for network errors.
    raw       : Original exception, if any.
    """

    def __init__(
        self,
        message: str,
        api_code: Optional[int] = None,
        raw: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.api_code = api_code
        self.raw = raw


# ── Result dataclass ───────────────────────────────────────────────────────────

@dataclass
class OrderResult:
    """
    Normalised order result returned by every placement function.

    All fields use their Binance naming convention so the mapping is obvious.
    """
    order_id:     int
    symbol:       str
    side:         str
    order_type:   str
    orig_qty:     str
    executed_qty: str
    status:       str
    avg_price:    str                        # "0" for unfilled orders
    client_order_id: str = ""
    raw_response: dict = field(default_factory=dict, repr=False)

    def is_filled(self) -> bool:
        """Return True when the order is fully filled."""
        return self.status == "FILLED"


# ── Internal helpers ───────────────────────────────────────────────────────────

def _extract_result(response: dict, order_type: str) -> OrderResult:
    """
    Parse a raw Binance API response dict into an `OrderResult`.
    Handles optional / missing fields gracefully.
    """
    return OrderResult(
        order_id        = response.get("orderId", 0),
        symbol          = response.get("symbol", ""),
        side            = response.get("side", ""),
        order_type      = response.get("type", order_type),
        orig_qty        = response.get("origQty", "0"),
        executed_qty    = response.get("executedQty", "0"),
        status          = response.get("status", "UNKNOWN"),
        avg_price       = response.get("avgPrice", response.get("price", "0")),
        client_order_id = response.get("clientOrderId", ""),
        raw_response    = response,
    )


def _handle_api_error(exc: BinanceAPIException, context: str) -> None:
    """Log a Binance API error and re-raise as `OrderError`."""
    logger.error(
        "Binance API error during %s: code=%s msg=%s",
        context, exc.status_code, exc.message,
    )
    raise OrderError(
        f"Binance API error [{exc.status_code}]: {exc.message}",
        api_code=exc.status_code,
        raw=exc,
    )


def _handle_network_error(exc: Exception, context: str) -> None:
    """Log a network error and re-raise as `OrderError`."""
    logger.error("Network/request error during %s: %s", context, exc)
    raise OrderError(
        f"Network error while placing {context} order: {exc}",
        raw=exc,
    )


# ── Order placement functions ──────────────────────────────────────────────────

def place_market_order(
    client: Client,
    symbol: str,
    side: str,
    quantity: Decimal,
) -> OrderResult:
    """
    Place a MARKET order on the Futures Testnet.

    Parameters
    ----------
    client   : Authenticated Binance client.
    symbol   : Trading pair (e.g. 'BTCUSDT').
    side     : 'BUY' or 'SELL'.
    quantity : Order quantity (Decimal for precision).

    Returns
    -------
    OrderResult
    """
    payload = {
        "symbol":   symbol,
        "side":     side,
        "type":     "MARKET",
        "quantity": str(quantity),
    }

    logger.debug("Placing MARKET order │ request payload: %s", payload)
    logger.info(
        "→ Placing MARKET %s │ %s  qty=%s", side, symbol, quantity
    )

    try:
        response: dict[str, Any] = client.futures_create_order(**payload)

    except BinanceAPIException as exc:
        _handle_api_error(exc, "MARKET order")

    except (BinanceRequestException, ConnectionError, TimeoutError) as exc:
        _handle_network_error(exc, "MARKET")

    logger.debug("MARKET order raw response: %s", response)
    result = _extract_result(response, "MARKET")
    logger.info(
        "✔ MARKET order placed │ orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id, result.status, result.executed_qty, result.avg_price,
    )
    return result


def place_limit_order(
    client: Client,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    time_in_force: str = "GTC",
) -> OrderResult:
    """
    Place a LIMIT order on the Futures Testnet.

    Parameters
    ----------
    client        : Authenticated Binance client.
    symbol        : Trading pair (e.g. 'BTCUSDT').
    side          : 'BUY' or 'SELL'.
    quantity      : Order quantity.
    price         : Limit price.
    time_in_force : 'GTC' (default), 'IOC', or 'FOK'.

    Returns
    -------
    OrderResult
    """
    payload = {
        "symbol":        symbol,
        "side":          side,
        "type":          "LIMIT",
        "quantity":      str(quantity),
        "price":         str(price),
        "timeInForce":   time_in_force,
    }

    logger.debug("Placing LIMIT order │ request payload: %s", payload)
    logger.info(
        "→ Placing LIMIT %s │ %s  qty=%s  price=%s  tif=%s",
        side, symbol, quantity, price, time_in_force,
    )

    try:
        response: dict[str, Any] = client.futures_create_order(**payload)

    except BinanceAPIException as exc:
        _handle_api_error(exc, "LIMIT order")

    except (BinanceRequestException, ConnectionError, TimeoutError) as exc:
        _handle_network_error(exc, "LIMIT")

    logger.debug("LIMIT order raw response: %s", response)
    result = _extract_result(response, "LIMIT")
    logger.info(
        "✔ LIMIT order placed │ orderId=%s status=%s executedQty=%s price=%s",
        result.order_id, result.status, result.executed_qty, result.avg_price,
    )
    return result


def place_stop_market_order(
    client: Client,
    symbol: str,
    side: str,
    quantity: Decimal,
    stop_price: Decimal,
) -> OrderResult:
    """
    Place a STOP_MARKET order (bonus feature).

    The order triggers a market fill when the mark price touches `stop_price`.

    Parameters
    ----------
    client     : Authenticated Binance client.
    symbol     : Trading pair (e.g. 'BTCUSDT').
    side       : 'BUY' or 'SELL'.
    quantity   : Order quantity.
    stop_price : Trigger price.

    Returns
    -------
    OrderResult
    """
    payload = {
        "symbol":    symbol,
        "side":      side,
        "type":      "STOP_MARKET",
        "quantity":  str(quantity),
        "stopPrice": str(stop_price),
    }

    logger.debug("Placing STOP_MARKET order │ request payload: %s", payload)
    logger.info(
        "→ Placing STOP_MARKET %s │ %s  qty=%s  stopPrice=%s",
        side, symbol, quantity, stop_price,
    )

    try:
        response: dict[str, Any] = client.futures_create_order(**payload)

    except BinanceAPIException as exc:
        _handle_api_error(exc, "STOP_MARKET order")

    except (BinanceRequestException, ConnectionError, TimeoutError) as exc:
        _handle_network_error(exc, "STOP_MARKET")

    logger.debug("STOP_MARKET order raw response: %s", response)
    result = _extract_result(response, "STOP_MARKET")
    logger.info(
        "✔ STOP_MARKET order placed │ orderId=%s status=%s stopPrice=%s",
        result.order_id, result.status, stop_price,
    )
    return result


# ── Top-level dispatcher ───────────────────────────────────────────────────────

def place_order(
    client: Client,
    validated_params: dict,
) -> OrderResult:
    """
    Route a validated parameter dict to the correct placement function.

    Parameters
    ----------
    client            : Authenticated Binance client.
    validated_params  : Output of `validators.validate_order_params()`.

    Returns
    -------
    OrderResult
    """
    order_type = validated_params["order_type"]
    symbol     = validated_params["symbol"]
    side       = validated_params["side"]
    quantity   = validated_params["quantity"]

    if order_type == "MARKET":
        return place_market_order(client, symbol, side, quantity)

    elif order_type == "LIMIT":
        return place_limit_order(
            client, symbol, side, quantity,
            price=validated_params["price"],
        )

    elif order_type == "STOP_MARKET":
        return place_stop_market_order(
            client, symbol, side, quantity,
            stop_price=validated_params["stop_price"],
        )

    else:
        raise OrderError(f"Unsupported order type: {order_type}")
