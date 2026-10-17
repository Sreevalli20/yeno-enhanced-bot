#!/usr/bin/env python3
"""Enhanced competition bot for the YeNo × Builderr Volume Bot Challenge.

Implements evidence-based strategy with adaptive sizing, spread analysis,
depth imbalance detection, and dynamic risk management while maintaining
strict contract compliance.

Production-ready for Render deployment with health check endpoint.
"""

from __future__ import annotations

import json
import math
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


# Configuration constants
MIN_SECONDS_TO_CLOSE = 15
MAX_ENTRY_SECONDS_TO_CLOSE = 120
FORCED_EXIT_SECONDS_TO_CLOSE = 15
MAX_REFERENCE_AGE_SECONDS = 2.0
MIN_REFERENCE_GAP_USD = 30.0
MAX_ENTRY_PRICE = 0.92
MAX_IMMEDIATE_ROUNDTRIP_LOSS_USD = 0.50
STOP_LOSS_PER_SHARE_USD = 0.15
MAX_CYCLES_PER_MARKET = 3
REENTRY_COOLDOWN_SECONDS = 2.0
BASE_TARGET_SHARES = 5.0
MIN_ASK_DEPTH_USD = 2.50
MIN_BID_DEPTH_USD = 2.50
MAX_SPREAD_PCT = 0.08
MIN_LIQUIDITY_RATIO = 0.30


def _parse_levels(rows: Any, *, reverse: bool) -> list[tuple[float, float]]:
    """Parse and validate order book levels."""
    output: list[tuple[float, float]] = []
    if not isinstance(rows, list):
        return output
    for row in rows:
        try:
            price = float(row[0])
            size = float(row[1])
        except (IndexError, TypeError, ValueError):
            continue
        if 0 < price < 1 and size > 0:
            output.append((price, size))
    return sorted(output, reverse=reverse)


def _calculate_fees(fills: list[tuple[float, float]]) -> float:
    """Calculate Polymarket-style dynamic fees plus YeNo 1% overlay."""
    gross = sum(price * shares for price, shares in fills)
    protocol = sum(0.07 * shares * price * (1 - price) for price, shares in fills)
    return round(protocol + 1e-12, 5) + round(gross * 0.01 + 1e-12, 5)


def _estimate_buy_cost(asks: Any, shares: float) -> tuple[float, float] | None:
    """Estimate cost to buy shares crossing the ask side."""
    levels = _parse_levels(asks, reverse=False)
    remaining = shares
    fills: list[tuple[float, float]] = []
    for price, available in levels:
        quantity = min(remaining, available)
        fills.append((price, quantity))
        remaining -= quantity
        if remaining <= 1e-9:
            break
    if remaining > 1e-9:
        return None
    gross = sum(price * quantity for price, quantity in fills)
    fees = _calculate_fees(fills)
    return gross, fees


def _estimate_sell_proceeds(bids: Any, shares: float) -> tuple[float, float] | None:
    """Estimate proceeds from selling shares crossing the bid side."""
    levels = _parse_levels(bids, reverse=True)
    remaining = shares
    fills: list[tuple[float, float]] = []
    for price, available in levels:
        quantity = min(remaining, available)
        fills.append((price, quantity))
        remaining -= quantity
        if remaining <= 1e-9:
            break
    if remaining > 1e-9:
        return None
    gross = sum(price * quantity for price, quantity in fills)
    fees = _calculate_fees(fills)
    return gross, fees


def _calculate_depth(book: dict[str, Any]) -> tuple[float, float]:
    """Calculate total notional depth on bid and ask sides."""
    bids = _parse_levels(book.get("bids", []), reverse=True)
    asks = _parse_levels(book.get("asks", []), reverse=False)
    bid_depth = sum(price * size for price, size in bids)
    ask_depth = sum(price * size for price, size in asks)
    return bid_depth, ask_depth


def _calculate_spread(book: dict[str, Any]) -> float:
    """Calculate relative spread as percentage of midpoint."""
    bids = _parse_levels(book.get("bids", []), reverse=True)
    asks = _parse_levels(book.get("asks", []), reverse=False)
    if not bids or not asks:
        return 1.0
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    midpoint = (best_bid + best_ask) / 2
    if midpoint <= 0:
        return 1.0
    return (best_ask - best_bid) / midpoint


def _calculate_imbalance(book: dict[str, Any]) -> float:
    """Calculate bid/ask imbalance (-1 to 1, positive favors bids)."""
    bid_levels = _parse_levels(book.get("bids", []), reverse=True)
    ask_levels = _parse_levels(book.get("asks", []), reverse=False)
    bid_notional = sum(price * size for price, size in bid_levels)
    ask_notional = sum(price * size for price, size in ask_levels)
    total = bid_notional + ask_notional
    if total <= 0:
        return 0.0
    return (bid_notional - ask_notional) / total


class EnhancedBot:
    """Enhanced trading bot with adaptive strategy."""

    def __init__(self) -> None:
        self.market_id: str | None = None
        self.position_was_open = False
        self.completed_cycles = 0
        self.last_flat_at = -math.inf
        self.last_buy_attempt_at = -math.inf
        self.total_pnl = 0.0
        self.entry_count = 0

    def decide(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Main decision function with comprehensive error handling."""
        try:
            return self._decide_internal(observation)
        except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
            return {"action": "HOLD"}

    def _decide_internal(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Internal decision logic."""
        market = observation["market"]
        account = observation["account"]
        books = observation["books"]
        now = float(observation["timestamp"])
        seconds = float(market["secondsToClose"])
        market_id = str(market["id"])
        position = account.get("position")

        # State reset on new market
        if market_id != self.market_id:
            self.market_id = market_id
            self.position_was_open = False
            self.completed_cycles = 0
            self.last_flat_at = -math.inf
            self.last_buy_attempt_at = -math.inf
            self.total_pnl = 0.0
            self.entry_count = 0

        # Track cycle completion
        if position is None and self.position_was_open:
            self.completed_cycles += 1
            self.last_flat_at = now
        self.position_was_open = position is not None

        # Exit logic when holding a position
        if position is not None:
            return self._handle_exit(position, books, seconds, account)

        # Entry filters
        if self.completed_cycles >= MAX_CYCLES_PER_MARKET:
            return {"action": "HOLD"}
        if now - self.last_flat_at < REENTRY_COOLDOWN_SECONDS - 1e-9:
            return {"action": "HOLD"}
        if now - self.last_buy_attempt_at < REENTRY_COOLDOWN_SECONDS - 1e-9:
            return {"action": "HOLD"}
        if not (MIN_SECONDS_TO_CLOSE < seconds <= MAX_ENTRY_SECONDS_TO_CLOSE):
            return {"action": "HOLD"}

        # Reference validation
        reference = observation.get("reference")
        if not isinstance(reference, dict):
            return {"action": "HOLD"}
        if bool(reference.get("targetProvisional", True)):
            return {"action": "HOLD"}
        if now - float(reference.get("observedAt", -math.inf)) > MAX_REFERENCE_AGE_SECONDS:
            return {"action": "HOLD"}
        if float(reference.get("targetObservedAt", math.inf)) > now + 1e-9:
            return {"action": "HOLD"}

        gap = float(reference["btcMidUsd"]) - float(reference["openingTargetUsd"])
        if abs(gap) < MIN_REFERENCE_GAP_USD - 1e-9:
            return {"action": "HOLD"}

        # Determine side from reference gap
        side = "YES" if gap >= 0 else "NO"
        book = books.get(side, {})

        # Validate book quality
        best_asks = _parse_levels(book.get("asks", []), reverse=False)
        if not best_asks or best_asks[0][0] > MAX_ENTRY_PRICE + 1e-9:
            return {"action": "HOLD"}

        spread = _calculate_spread(book)
        if spread > MAX_SPREAD_PCT:
            return {"action": "HOLD"}

        bid_depth, ask_depth = _calculate_depth(book)
        if ask_depth < MIN_ASK_DEPTH_USD:
            return {"action": "HOLD"}
        if bid_depth < MIN_BID_DEPTH_USD:
            return {"action": "HOLD"}

        imbalance = _calculate_imbalance(book)
        if (side == "YES" and imbalance < -MIN_LIQUIDITY_RATIO) or (side == "NO" and imbalance > MIN_LIQUIDITY_RATIO):
            return {"action": "HOLD"}

        # Adaptive sizing based on remaining cash and performance
        cash = float(account["cashUsd"])
        max_buy = min(cash, float(observation["rules"]["maximumBuyCashUsd"]))
        base_shares = BASE_TARGET_SHARES

        # Scale down if drawdown or low cash
        if self.total_pnl < -0.50:
            base_shares *= 0.5
        elif cash < 6.0:
            base_shares *= 0.8

        # Scale up if performing well and have cash
        if self.total_pnl > 1.0 and cash > 8.0:
            base_shares *= 1.2

        target_shares = min(base_shares, 10.0)

        # Check execution feasibility
        buy_cost = _estimate_buy_cost(book.get("asks", []), target_shares)
        sell_proceeds = _estimate_sell_proceeds(book.get("bids", []), target_shares)
        if buy_cost is None or sell_proceeds is None:
            return {"action": "HOLD"}

        gross, fees = buy_cost
        sell_gross, sell_fees = sell_proceeds
        immediate_loss = sell_gross - sell_fees - gross - fees

        if immediate_loss < -MAX_IMMEDIATE_ROUNDTRIP_LOSS_USD - 1e-9:
            return {"action": "HOLD"}

        total_cost = gross + fees
        if total_cost > max_buy + 1e-9:
            return {"action": "HOLD"}

        self.last_buy_attempt_at = now
        self.entry_count += 1
        return {"action": "BUY", "outcome": side, "maxCashUsd": round(total_cost, 6)}

    def _handle_exit(
        self, position: dict[str, Any], books: dict[str, Any], seconds: float, account: dict[str, Any]
    ) -> dict[str, Any]:
        """Handle exit logic for existing position."""
        side = str(position["outcome"])
        shares = float(position["shares"])
        book = books.get(side, {})

        sell_proceeds = _estimate_sell_proceeds(book.get("bids", []), shares)
        if sell_proceeds is None:
            return {"action": "HOLD"}

        sell_gross, sell_fees = sell_proceeds
        paid = float(position["buy_gross_usd"]) + float(position["buy_fees_usd"])
        received = float(position.get("sell_gross_usd", 0)) - float(position.get("sell_fees_usd", 0))
        full_cycle_pnl = received + sell_gross - sell_fees - paid

        # Exit conditions
        if full_cycle_pnl >= -1e-9:
            return {"action": "SELL"}
        if full_cycle_pnl <= -STOP_LOSS_PER_SHARE_USD * shares + 1e-9:
            return {"action": "SELL"}
        if seconds <= FORCED_EXIT_SECONDS_TO_CLOSE + 1e-9:
            return {"action": "SELL"}

        return {"action": "HOLD"}


BOT = EnhancedBot()


def decide(observation: dict[str, Any]) -> dict[str, Any]:
    """Entry point for the /decide endpoint."""
    return BOT.decide(observation)


# Homepage HTML with professional chatbot-style interface
HOMEPAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YeNo Enhanced Bot - Paper Trading Research</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .header h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 10px;
        }
        .disclaimer {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
            font-size: 14px;
            color: #856404;
        }
        .disclaimer strong {
            display: block;
            margin-bottom: 5px;
        }
        .chat-container {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .input-section {
            margin-bottom: 20px;
        }
        .input-section label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }
        textarea {
            width: 100%;
            min-height: 200px;
            padding: 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            resize: vertical;
        }
        textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        .button-group {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }
        .run-btn {
            background: #667eea;
            color: white;
        }
        .run-btn:hover {
            background: #5568d3;
        }
        .sample-btn {
            background: #6c757d;
            color: white;
        }
        .sample-btn:hover {
            background: #5a6268;
        }
        .results-section {
            margin-top: 20px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            display: none;
        }
        .results-section.visible {
            display: block;
        }
        .results-section h3 {
            color: #333;
            margin-bottom: 15px;
        }
        .result-card {
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 10px;
            border-left: 4px solid #28a745;
        }
        .result-card.error {
            border-left-color: #dc3545;
        }
        .result-card .label {
            font-weight: 600;
            color: #666;
            margin-bottom: 5px;
        }
        .result-card .value {
            font-size: 18px;
            color: #333;
        }
        .result-card .json {
            font-family: 'Courier New', monospace;
            font-size: 13px;
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin-top: 10px;
            overflow-x: auto;
        }
        .info-section {
            margin-top: 30px;
            padding: 20px;
            background: #e7f3ff;
            border-radius: 8px;
        }
        .info-section h3 {
            color: #0056b3;
            margin-bottom: 10px;
        }
        .info-section p {
            color: #333;
            line-height: 1.6;
            margin-bottom: 10px;
        }
        .info-section ul {
            margin-left: 20px;
            color: #333;
            line-height: 1.6;
        }
        @media (max-width: 768px) {
            .header, .chat-container {
                padding: 20px;
            }
            .button-group {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>YeNo Enhanced Bot - Paper Trading Research</h1>
            <p style="color: #666; margin-top: 10px;">Competition submission for the YeNo × Builderr Volume Bot Challenge</p>
            
            <div class="disclaimer">
                <strong>IMPORTANT DISCLAIMER</strong>
                This is a paper-trading research bot for a software competition. It does NOT execute real trades, does NOT connect to live markets, does NOT use real money, and does NOT provide financial advice. All decisions are based on simulated historical data for research purposes only.
            </div>
        </div>

        <div class="chat-container">
            <div class="input-section">
                <label for="observation">Market Observation (JSON)</label>
                <textarea id="observation" placeholder="Paste your market observation JSON here or click 'Load Sample Data'"></textarea>
                
                <div class="button-group">
                    <button class="run-btn" onclick="runAnalysis()">Run Analysis</button>
                    <button class="sample-btn" onclick="loadSampleData()">Load Sample Data</button>
                </div>
            </div>

            <div class="results-section" id="results">
                <h3>Analysis Results</h3>
                <div class="result-card" id="result-card">
                    <div class="label">Decision</div>
                    <div class="value" id="decision-value">-</div>
                    <div class="json" id="decision-json"></div>
                </div>
            </div>

            <div class="info-section">
                <h3>About This Bot</h3>
                <p>This bot implements an evidence-based trading strategy for the YeNo × Builderr Volume Bot Challenge. It analyzes BTC five-minute Up/Down markets using order book data and reference price signals.</p>
                
                <h3>Key Features</h3>
                <ul>
                    <li>Adaptive position sizing based on remaining cash and performance</li>
                    <li>Spread analysis to reject wide-spread markets</li>
                    <li>Depth requirements for liquidity validation</li>
                    <li>Imbalance detection to align with order flow</li>
                    <li>Strict compliance with the official evaluator contract</li>
                </ul>

                <h3>Compliance</h3>
                <ul>
                    <li>$10 starting simulated cash</li>
                    <li>$5 maximum fee-inclusive BUY</li>
                    <li>24-hour evaluation window</li>
                    <li>$1,000 eligible volume target</li>
                    <li>One position or pending BUY at a time</li>
                    <li>15-second no-entry zone before expiry</li>
                </ul>

                <h3>API Endpoints</h3>
                <ul>
                    <li><code>GET /health</code> - Health check endpoint</li>
                    <li><code>POST /decide</code> - Official competition decision endpoint</li>
                </ul>
            </div>
        </div>
    </div>

    <script>
        const SAMPLE_OBSERVATION = {
            "schemaVersion": 1,
            "timestamp": 1789880823.619,
            "market": {
                "id": "sample-btc-5m-market",
                "secondsToClose": 84
            },
            "account": {
                "cashUsd": 10,
                "eligibleVolumeUsd": 0,
                "completedCycles": 0,
                "position": null
            },
            "rules": {
                "maximumBuyCashUsd": 5,
                "targetVolumeUsd": 1000,
                "evaluationWindowHours": 24,
                "onePositionAtATime": true,
                "buyFeesIncludedInMaximum": true
            },
            "reference": {
                "btcMidUsd": 80482.155,
                "openingTargetUsd": 80424.946,
                "observedAt": 1789880823.019,
                "targetObservedAt": 1789880814.203,
                "targetProvisional": false
            },
            "books": {
                "YES": {
                    "bids": [[0.49, 100]],
                    "asks": [[0.50, 100]],
                    "minOrderSize": 5
                },
                "NO": {
                    "bids": [[0.49, 100]],
                    "asks": [[0.50, 100]],
                    "minOrderSize": 5
                }
            }
        };

        function loadSampleData() {
            document.getElementById('observation').value = JSON.stringify(SAMPLE_OBSERVATION, null, 2);
        }

        async function runAnalysis() {
            const textarea = document.getElementById('observation');
            const resultsSection = document.getElementById('results');
            const resultCard = document.getElementById('result-card');
            const decisionValue = document.getElementById('decision-value');
            const decisionJson = document.getElementById('decision-json');

            try {
                const observation = JSON.parse(textarea.value);
                
                decisionValue.textContent = 'Processing...';
                resultsSection.classList.add('visible');
                resultCard.classList.remove('error');

                const response = await fetch('/decide', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(observation)
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const decision = await response.json();
                
                decisionValue.textContent = decision.action;
                decisionJson.textContent = JSON.stringify(decision, null, 2);
                
                if (decision.action === 'BUY') {
                    decisionValue.textContent += ` ${decision.outcome} ($${decision.maxCashUsd.toFixed(2)})`;
                }

            } catch (error) {
                resultsSection.classList.add('visible');
                resultCard.classList.add('error');
                decisionValue.textContent = 'Error';
                decisionJson.textContent = error.message;
            }
        }
    </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests for homepage and health check."""
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            body = HOMEPAGE_HTML.encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            body = json.dumps({"status": "healthy"}).encode()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests for /decide endpoint."""
        if self.path != "/decide":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 10000:  # 10KB limit
                self.send_error(413)
                return
            response = decide(json.loads(self.rfile.read(length)))
            body = json.dumps(response, separators=(",", ":")).encode()
        except Exception:
            self.send_error(400)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: Any) -> None:
        """Suppress default logging."""
        return


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting YeNo bot on {host}:{port}")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
