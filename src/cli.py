"""
cli.py
------
Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage examples
--------------
  # Market BUY
  python -m src.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  # Limit SELL
  python -m src.cli --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3200

  # Stop-Market (bonus)
  python -m src.cli --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000

Design
------
  - argparse handles all CLI argument parsing.
  - Validators run before any network call.
  - A rich order summary is printed before submission.
  - The response is printed in a structured, readable block.
  - Every non-zero exit carries an informative message to stderr.
"""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal
from typing import Optional

from src.client import get_futures_client, ping_exchange
from src.logging_config import get_logger
from src.orders import OrderError, OrderResult, place_order
from src.validators import ValidationError, validate_order_params

logger = get_logger(__name__)


# ── Pretty-print helpers ───────────────────────────────────────────────────────

_LINE = "─" * 56


def _banner(title: str) -> None:
    print(f"\n{_LINE}")
    print(f"  {title}")
    print(_LINE)


def _print_request_summary(params: dict) -> None:
    """Print the validated order details before sending to the exchange."""
    _banner("📋  ORDER REQUEST SUMMARY")
    print(f"  Symbol     : {params['symbol']}")
    print(f"  Side       : {params['side']}")
    print(f"  Type       : {params['order_type']}")
    print(f"  Quantity   : {params['quantity']}")

    if "price" in params:
        print(f"  Limit Price: {params['price']}")
    if "stop_price" in params:
        print(f"  Stop Price : {params['stop_price']}")

    print(_LINE + "\n")


def _print_order_result(result: OrderResult) -> None:
    """Print the exchange response in a structured block."""
    filled = result.is_filled()
    status_icon = "✅" if filled else "⏳"

    _banner(f"{status_icon}  ORDER RESPONSE")
    print(f"  Order ID      : {result.order_id}")
    print(f"  Client Ord ID : {result.client_order_id or 'N/A'}")
    print(f"  Symbol        : {result.symbol}")
    print(f"  Side          : {result.side}")
    print(f"  Type          : {result.order_type}")
    print(f"  Status        : {result.status}")
    print(f"  Orig Qty      : {result.orig_qty}")
    print(f"  Executed Qty  : {result.executed_qty}")
    print(f"  Avg Price     : {result.avg_price or 'N/A'}")
    print(_LINE)

    if filled:
        print("\n  ✅  Order executed successfully!\n")
    else:
        print(f"\n  ⏳  Order placed with status: {result.status}\n")


def _print_error(message: str) -> None:
    """Print a formatted error block to stderr."""
    print(f"\n{_LINE}", file=sys.stderr)
    print(f"  ❌  ERROR", file=sys.stderr)
    print(_LINE, file=sys.stderr)
    print(f"  {message}", file=sys.stderr)
    print(_LINE + "\n", file=sys.stderr)


# ── Argument parser ────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description=(
            "Binance USDT-M Futures Testnet Trading Bot\n"
            "Place MARKET, LIMIT, and STOP_MARKET orders from the command line."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
examples:
  Market BUY  0.01 BTC:
    python -m src.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

  Limit SELL  0.5 ETH at $3,200:
    python -m src.cli --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3200

  Stop-Market SELL (trigger at $58,000):
    python -m src.cli --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000
        """,
    )

    parser.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair (e.g. BTCUSDT, ETHUSDT).",
    )
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        metavar="SIDE",
        help="Order direction: BUY or SELL.",
    )
    parser.add_argument(
        "--type", "-t",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"],
        metavar="TYPE",
        help="Order type: MARKET, LIMIT, or STOP_MARKET.",
    )
    parser.add_argument(
        "--quantity", "-q",
        required=True,
        metavar="QTY",
        help="Quantity to buy/sell (e.g. 0.01).",
    )
    parser.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price (required for LIMIT orders).",
    )
    parser.add_argument(
        "--stop-price",
        default=None,
        metavar="STOP_PRICE",
        help="Stop trigger price (required for STOP_MARKET orders).",
    )
    parser.add_argument(
        "--skip-ping",
        action="store_true",
        help="Skip the initial exchange connectivity check.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate inputs and print the order summary without "
            "sending anything to the exchange."
        ),
    )

    return parser


# ── Main entrypoint ────────────────────────────────────────────────────────────

def main() -> int:
    """
    Parse CLI arguments, validate, and place the order.

    Returns an exit code (0 = success, non-zero = failure).
    """
    parser = _build_parser()
    args = parser.parse_args()

    logger.info(
        "Bot started │ symbol=%s side=%s type=%s qty=%s",
        args.symbol, args.side, args.order_type, args.quantity,
    )

    # ── 1. Validate inputs ───────────────────────────────────────────────────
    try:
        validated = validate_order_params(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            stop_price=args.stop_price,
        )
    except ValidationError as exc:
        _print_error(f"Validation failed: {exc}")
        logger.error("Validation error: %s", exc)
        return 1

    # ── 2. Print request summary ─────────────────────────────────────────────
    _print_request_summary(validated)

    if args.dry_run:
        print("  🔍  Dry-run mode – no order was sent to the exchange.\n")
        logger.info("Dry-run mode – exiting without placing order.")
        return 0

    # ── 3. Initialise Binance client ─────────────────────────────────────────
    try:
        client = get_futures_client()
    except EnvironmentError as exc:
        _print_error(str(exc))
        logger.error("Client init error: %s", exc)
        return 1

    # ── 4. Connectivity check ────────────────────────────────────────────────
    if not args.skip_ping:
        if not ping_exchange(client):
            _print_error(
                "Cannot reach the Binance Futures Testnet. "
                "Check your internet connection and try again."
            )
            return 1

    # ── 5. Place order ───────────────────────────────────────────────────────
    try:
        result = place_order(client, validated)
    except OrderError as exc:
        _print_error(str(exc))
        logger.error("Order placement failed: %s", exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        _print_error(f"Unexpected error: {exc}")
        logger.exception("Unexpected error during order placement.")
        return 1

    # ── 6. Print response ────────────────────────────────────────────────────
    _print_order_result(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
