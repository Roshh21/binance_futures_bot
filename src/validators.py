"""
validators.py
-------------
Input validation for all CLI arguments before they reach the Binance API.

Design goals:
  - Fail fast with descriptive messages so the user never gets a cryptic
    exchange error for a typo.
  - Return clean, normalised values (upper-cased strings, Decimal quantities)
    so downstream code never has to sanitise again.
  - Keep every rule self-contained and easily unit-testable.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from src.logging_config import get_logger

logger = get_logger(__name__)

# ── Supported constants ────────────────────────────────────────────────────────
VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}   # STOP_MARKET = bonus

# Basic safeguards – the exchange will enforce its own minimums per symbol,
# but we reject obviously nonsensical values early.
MIN_QUANTITY = Decimal("0.000001")
MAX_QUANTITY = Decimal("1_000_000")
MIN_PRICE = Decimal("0.00001")
MAX_PRICE = Decimal("10_000_000")


class ValidationError(ValueError):
    """Raised when any input fails validation; carries a human-readable message."""


# ── Individual validators ──────────────────────────────────────────────────────

def validate_symbol(symbol: str) -> str:
    """
    Return the uppercased trading pair or raise ValidationError.

    Rules
    -----
    - Must be a non-empty alphabetic string (letters only, no spaces/hyphens).
    - Converted to uppercase so the caller never needs to worry about case.
    """
    if not symbol:
        raise ValidationError("Symbol cannot be empty.")

    normalised = symbol.strip().upper()

    if not normalised.isalpha():
        raise ValidationError(
            f"Invalid symbol '{symbol}'. "
            "Symbols must contain letters only (e.g. BTCUSDT, ETHUSDT)."
        )

    logger.debug("Symbol validated: %s", normalised)
    return normalised


def validate_side(side: str) -> str:
    """
    Return 'BUY' or 'SELL', or raise ValidationError.
    """
    if not side:
        raise ValidationError("Side cannot be empty.")

    normalised = side.strip().upper()

    if normalised not in VALID_SIDES:
        raise ValidationError(
            f"Invalid side '{side}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )

    logger.debug("Side validated: %s", normalised)
    return normalised


def validate_order_type(order_type: str) -> str:
    """
    Return the normalised order type string, or raise ValidationError.
    """
    if not order_type:
        raise ValidationError("Order type cannot be empty.")

    normalised = order_type.strip().upper()

    if normalised not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )

    logger.debug("Order type validated: %s", normalised)
    return normalised


def validate_quantity(quantity: str | float | Decimal) -> Decimal:
    """
    Parse and validate the order quantity.

    Returns a Decimal for precision arithmetic.
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid quantity '{quantity}'. Must be a positive number."
        )

    if qty <= 0:
        raise ValidationError(
            f"Quantity must be greater than zero (got {quantity})."
        )

    if qty < MIN_QUANTITY:
        raise ValidationError(
            f"Quantity {quantity} is below the minimum allowed ({MIN_QUANTITY})."
        )

    if qty > MAX_QUANTITY:
        raise ValidationError(
            f"Quantity {quantity} exceeds the maximum allowed ({MAX_QUANTITY})."
        )

    logger.debug("Quantity validated: %s", qty)
    return qty


def validate_price(price: str | float | Decimal) -> Decimal:
    """
    Parse and validate a limit/stop price.

    Returns a Decimal for precision arithmetic.
    """
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValidationError(
            f"Invalid price '{price}'. Must be a positive number."
        )

    if p <= 0:
        raise ValidationError(
            f"Price must be greater than zero (got {price})."
        )

    if p < MIN_PRICE:
        raise ValidationError(
            f"Price {price} is below the minimum allowed ({MIN_PRICE})."
        )

    if p > MAX_PRICE:
        raise ValidationError(
            f"Price {price} exceeds the maximum allowed ({MAX_PRICE})."
        )

    logger.debug("Price validated: %s", p)
    return p


def validate_order_params(
    *,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    stop_price: Optional[str] = None,
) -> dict:
    """
    Validate every parameter for an order and return a clean, typed dict.

    Parameters
    ----------
    symbol      : Trading pair string (e.g. 'BTCUSDT').
    side        : 'BUY' or 'SELL'.
    order_type  : 'MARKET', 'LIMIT', or 'STOP_MARKET'.
    quantity    : Positive numeric string.
    price       : Limit price (required for LIMIT orders).
    stop_price  : Trigger price (required for STOP_MARKET orders).

    Returns
    -------
    dict with keys: symbol, side, order_type, quantity, price (opt), stop_price (opt)

    Raises
    ------
    ValidationError on any invalid input.
    """
    logger.debug(
        "Validating order params: symbol=%s side=%s type=%s qty=%s price=%s stop=%s",
        symbol, side, order_type, quantity, price, stop_price,
    )

    validated: dict = {
        "symbol":     validate_symbol(symbol),
        "side":       validate_side(side),
        "order_type": validate_order_type(order_type),
        "quantity":   validate_quantity(quantity),
    }

    ot = validated["order_type"]

    # ── LIMIT orders require a limit price ──────────────────────────────────
    if ot == "LIMIT":
        if price is None:
            raise ValidationError("A --price is required for LIMIT orders.")
        validated["price"] = validate_price(price)

    # ── STOP_MARKET orders require a stop price ──────────────────────────────
    elif ot == "STOP_MARKET":
        if stop_price is None:
            raise ValidationError("A --stop-price is required for STOP_MARKET orders.")
        validated["stop_price"] = validate_price(stop_price)

    # ── MARKET orders must NOT have a price ──────────────────────────────────
    elif ot == "MARKET" and price is not None:
        logger.warning(
            "Price '%s' supplied for MARKET order – it will be ignored.", price
        )

    logger.info(
        "✔ Validation passed │ %s %s %s qty=%s",
        validated["symbol"], validated["side"], ot, validated["quantity"],
    )
    return validated
