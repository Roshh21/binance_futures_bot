# Binance Futures Testnet Trading Bot

A professional, modular Python CLI trading bot for the **Binance USDT-M Futures Testnet**.  
Supports `MARKET`, `LIMIT`, and `STOP_MARKET` orders with structured logging, full input validation, and clean separation of concerns.

>  **Tested and working** — all order types confirmed on Binance Futures Testnet (May 2026)

---

##  Prerequisites

| Requirement | Version |
|-------------|---------|
| Python      | 3.9+    |
| pip         | latest  |

---

## Binance Testnet Setup

### Step 1 – Create a Testnet Account

1. Open [https://testnet.binancefuture.com](https://testnet.binancefuture.com) in your browser.
2. Click **"Log In with GitHub"** — no separate registration needed.
3. Authorise the GitHub OAuth prompt.

### Step 2 – Generate API Credentials

1. After logging in, click your username (top-right) → **"API Key"**.
2. Click **"Generate Key"**.
3. Copy the **API Key** and **Secret Key** — the secret is shown only once.

> **These are testnet-only credentials. They have no access to real funds.**

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/binance_futures_bot.git
cd binance_futures_bot
```

### 2. Create a virtual environment

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and paste your testnet credentials:

```dotenv
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here
```

>  `.env` is listed in `.gitignore` and will never be committed to version control.

---

## Usage

All commands are run from the project root directory.

```
python -m src.cli [OPTIONS]
```

### Required Arguments

| Flag | Description | Example |
|------|-------------|---------|
| `--symbol` / `-s` | Trading pair | `BTCUSDT` |
| `--side` | Order direction | `BUY` or `SELL` |
| `--type` / `-t` | Order type | `MARKET`, `LIMIT`, `STOP_MARKET` |
| `--quantity` / `-q` | Amount to trade | `0.01` |

### Conditional Arguments

| Flag | Required when | Description |
|------|--------------|-------------|
| `--price` / `-p` | `--type LIMIT` | Limit price |
| `--stop-price` | `--type STOP_MARKET` | Stop trigger price |

### Optional Flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Validate and print summary without sending to exchange |
| `--skip-ping` | Skip connectivity check (useful for CI) |

---

## Run Examples

### Dry-run (validate only — no order sent)

```bash
python -m src.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

**Real output:**
```
2026-05-20 21:27:33  INFO  __main__       | Bot started | symbol=BTCUSDT side=BUY type=MARKET qty=0.01
2026-05-20 21:27:33  INFO  src.validators | ✔ Validation passed | BTCUSDT BUY MARKET qty=0.01

────────────────────────────────────────────────────────
  📋  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.01
────────────────────────────────────────────────────────

  🔍  Dry-run mode — no order was sent to the exchange.

2026-05-20 21:27:33  INFO  __main__ | Dry-run mode — exiting without placing order.
```

---

### Limit SELL — 0.5 ETH at $3,200

```bash
python -m src.cli --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.5 --price 3200
```

**Real output:**
```
2026-05-20 21:27:46  INFO  __main__       | Bot started | symbol=ETHUSDT side=SELL type=LIMIT qty=0.5
2026-05-20 21:27:46  INFO  src.validators | ✔ Validation passed | ETHUSDT SELL LIMIT qty=0.5

────────────────────────────────────────────────────────
  📋  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────
  Symbol     : ETHUSDT
  Side       : SELL
  Type       : LIMIT
  Quantity   : 0.5
  Limit Price: 3200
────────────────────────────────────────────────────────

2026-05-20 21:27:46  INFO  src.client | Initialising Binance Futures Testnet client …
2026-05-20 21:27:47  INFO  src.client | ✔ Exchange ping successful — testnet is reachable.
2026-05-20 21:27:47  INFO  src.orders | → Placing LIMIT SELL | ETHUSDT  qty=0.5  price=3200  tif=GTC
2026-05-20 21:27:48  INFO  src.orders | ✔ LIMIT order placed | orderId=8717583745 status=NEW executedQty=0.000 price=0.00

────────────────────────────────────────────────────────
  ⏳  ORDER RESPONSE
────────────────────────────────────────────────────────
  Order ID      : 8717583745
  Client Ord ID : MybQHyeHKYS2FyP3jwmMkD
  Symbol        : ETHUSDT
  Side          : SELL
  Type          : LIMIT
  Status        : NEW
  Orig Qty      : 0.500
  Executed Qty  : 0.000
  Avg Price     : 0.00
────────────────────────────────────────────────────────

  ⏳  Order placed with status: NEW
```

> LIMIT orders return `NEW` — the order is live on the book, waiting for the market price to reach $3,200.

---

###  Market SELL — 0.01 BTC

```bash
python -m src.cli --symbol BTCUSDT --side SELL --type MARKET --quantity 0.01
```

**Real output:**
```
2026-05-20 21:29:16  INFO  __main__       | Bot started | symbol=BTCUSDT side=SELL type=MARKET qty=0.01
2026-05-20 21:29:16  INFO  src.validators | ✔ Validation passed | BTCUSDT SELL MARKET qty=0.01

────────────────────────────────────────────────────────
  📋  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : SELL
  Type       : MARKET
  Quantity   : 0.01
────────────────────────────────────────────────────────

2026-05-20 21:29:16  INFO  src.client | Initialising Binance Futures Testnet client …
2026-05-20 21:29:16  INFO  src.client | ✔ Exchange ping successful — testnet is reachable.
2026-05-20 21:29:16  INFO  src.orders | → Placing MARKET SELL | BTCUSDT  qty=0.01
2026-05-20 21:29:17  INFO  src.orders | ✔ MARKET order placed | orderId=13168538901 status=NEW executedQty=0.0000 avgPrice=0.00

────────────────────────────────────────────────────────
  ⏳  ORDER RESPONSE
────────────────────────────────────────────────────────
  Order ID      : 13168538901
  Client Ord ID : 6NPGAlqWNQkO6sWp3hlb2W
  Symbol        : BTCUSDT
  Side          : SELL
  Type          : MARKET
  Status        : NEW
  Orig Qty      : 0.0100
  Executed Qty  : 0.0000
  Avg Price     : 0.00
────────────────────────────────────────────────────────

  ⏳  Order placed with status: NEW
```

---

### Stop-Market SELL — trigger at $58,000 (bonus feature)

```bash
python -m src.cli --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 58000
```

---

### Help

```bash
python -m src.cli --help
```

---

## Logging

All activity is written to `logs/trading_bot.log` with rotating file support (5 MB per file, 3 backups).

| Level | Destination | Content |
|-------|-------------|---------|
| `DEBUG` | File only | Full request/response payloads, all internal state |
| `INFO` | File + Console | Order lifecycle events, connectivity checks |
| `WARNING` | File + Console | Non-fatal issues (e.g. price supplied for MARKET order) |
| `ERROR` | File + Console | API errors, network failures, validation failures |

Sample log output for all order types is in `logs/sample_trading_bot.log`.

---

##  Module Reference

### `src/logging_config.py`
Configures the root Python logger with colour-coded console output (INFO+) and a rotating file handler writing to `logs/trading_bot.log` (DEBUG+). Exposes a `get_logger(name)` factory used by every other module.

### `src/client.py`
- `get_futures_client()` — loads credentials from `.env`, returns a `python-binance` `Client` pointed at the Futures Testnet
- `ping_exchange(client)` — lightweight connectivity check run at startup

### `src/validators.py`
- Individual validators: `validate_symbol()`, `validate_side()`, `validate_order_type()`, `validate_quantity()`, `validate_price()`
- `validate_order_params()` — top-level dispatcher; validates all fields and returns a clean typed `dict`
- Raises `ValidationError` (a `ValueError` subclass) on any failure

### `src/orders.py`
- `place_market_order()`, `place_limit_order()`, `place_stop_market_order()` — individual order functions
- `place_order(client, validated_params)` — dispatcher routing to the correct function
- Returns an `OrderResult` dataclass; raises `OrderError` on failure

### `src/cli.py`
- `main()` — argparse → validate → ping → place → print
- `_print_request_summary()` and `_print_order_result()` — structured console UX
- Exit code `0` on success, `1` on any failure

---

##  Security Notes

- API keys are loaded exclusively from environment variables via `python-dotenv`.
- No secrets appear in code, logs, or output.
- `.env` is `.gitignore`d — it will never be committed.
- The bot exclusively targets the **testnet** — real-money endpoints are never called.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `python-binance` | 1.0.19 | Official Binance API client |
| `python-dotenv` | 1.0.1 | `.env` file loading |

---
