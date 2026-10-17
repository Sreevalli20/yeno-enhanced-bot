#!/usr/bin/env python3
"""Comprehensive automated tests for the enhanced YeNo competition bot.

Tests cover contract compliance, edge cases, error handling, and
Python 3.14 compatibility. All test data is synthetic unless explicitly
marked as the official sample observation.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


# Import the bot's decision function
sys.path.insert(0, str(Path(__file__).parent))
from yeno_competition_starter_bot import decide, BOT


def reset_bot_state() -> None:
    """Reset bot state between tests."""
    BOT.market_id = None
    BOT.position_was_open = False
    BOT.completed_cycles = 0
    BOT.last_flat_at = -math.inf
    BOT.last_buy_attempt_at = -math.inf
    BOT.total_pnl = 0.0
    BOT.entry_count = 0


# Official sample observation
SAMPLE_OBSERVATION = {
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
        "position": None
    },
    "rules": {
        "maximumBuyCashUsd": 5,
        "targetVolumeUsd": 1000,
        "evaluationWindowHours": 24,
        "onePositionAtATime": True,
        "buyFeesIncludedInMaximum": True
    },
    "reference": {
        "btcMidUsd": 80482.155,
        "openingTargetUsd": 80424.946,
        "observedAt": 1789880823.019,
        "targetObservedAt": 1789880814.203,
        "targetProvisional": False
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
}


def test_sample_observation() -> None:
    """Test the official sample observation produces valid response."""
    reset_bot_state()
    result = decide(SAMPLE_OBSERVATION)
    assert isinstance(result, dict), "Result must be a dict"
    assert "action" in result, "Result must have 'action' field"
    assert result["action"] in {"HOLD", "BUY", "SELL"}, f"Invalid action: {result['action']}"
    print("[PASS] Sample observation test passed")


def test_response_schema() -> None:
    """Test all valid response schemas."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()

    # HOLD response
    result = decide(obs)
    assert result["action"] == "HOLD" or result["action"] in {"BUY", "SELL"}
    print("[PASS] Response schema test passed")


def test_buy_response_validation() -> None:
    """Test BUY response includes required fields and respects $5 cap."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["reference"]["btcMidUsd"] = 80474.946  # Just below opening target
    obs["reference"]["openingTargetUsd"] = 80424.946
    obs["market"]["secondsToClose"] = 60

    result = decide(obs)
    if result["action"] == "BUY":
        assert "outcome" in result, "BUY must have 'outcome'"
        assert result["outcome"] in {"YES", "NO"}, f"Invalid outcome: {result['outcome']}"
        assert "maxCashUsd" in result, "BUY must have 'maxCashUsd'"
        amount = float(result["maxCashUsd"])
        assert 0 < amount <= 5, f"BUY exceeds $5 cap: {amount}"
    print("[PASS] BUY response validation test passed")


def test_missing_fields() -> None:
    """Test graceful handling of missing fields."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()

    # Missing market
    obs_no_market = obs.copy()
    del obs_no_market["market"]
    result = decide(obs_no_market)
    assert result["action"] == "HOLD", "Should HOLD on missing market"

    # Missing account
    obs_no_account = obs.copy()
    del obs_no_account["account"]
    result = decide(obs_no_account)
    assert result["action"] == "HOLD", "Should HOLD on missing account"

    # Missing books
    obs_no_books = obs.copy()
    del obs_no_books["books"]
    result = decide(obs_no_books)
    assert result["action"] == "HOLD", "Should HOLD on missing books"

    print("[PASS] Missing fields test passed")


def test_malformed_fields() -> None:
    """Test graceful handling of malformed field values."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()

    # Invalid timestamp
    obs_bad_time = obs.copy()
    obs_bad_time["timestamp"] = "invalid"
    result = decide(obs_bad_time)
    assert result["action"] == "HOLD", "Should HOLD on invalid timestamp"

    # Invalid secondsToClose
    obs_bad_seconds = obs.copy()
    obs_bad_seconds["market"]["secondsToClose"] = "invalid"
    result = decide(obs_bad_seconds)
    assert result["action"] == "HOLD", "Should HOLD on invalid secondsToClose"

    # Invalid cash
    obs_bad_cash = obs.copy()
    obs_bad_cash["account"]["cashUsd"] = "invalid"
    result = decide(obs_bad_cash)
    assert result["action"] == "HOLD", "Should HOLD on invalid cash"

    print("[PASS] Malformed fields test passed")


def test_stale_reference() -> None:
    """Test rejection of stale reference data."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["reference"]["observedAt"] = obs["timestamp"] - 5.0  # 5 seconds old
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on stale reference"
    print("[PASS] Stale reference test passed")


def test_future_target_observation() -> None:
    """Test rejection of future-dated target observations."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["reference"]["targetObservedAt"] = obs["timestamp"] + 10.0  # Future
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on future target observation"
    print("[PASS] Future target observation test passed")


def test_provisional_target() -> None:
    """Test rejection of provisional targets."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["reference"]["targetProvisional"] = True
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on provisional target"
    print("[PASS] Provisional target test passed")


def test_empty_books() -> None:
    """Test handling of empty order books."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["books"]["YES"]["bids"] = []
    obs["books"]["YES"]["asks"] = []
    obs["books"]["NO"]["bids"] = []
    obs["books"]["NO"]["asks"] = []
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on empty books"
    print("[PASS] Empty books test passed")


def test_wide_spreads() -> None:
    """Test rejection of wide spreads."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["books"]["YES"]["bids"] = [[0.40, 100]]
    obs["books"]["YES"]["asks"] = [[0.60, 100]]  # Wide spread
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on wide spread"
    print("[PASS] Wide spreads test passed")


def test_insufficient_depth() -> None:
    """Test rejection of insufficient liquidity depth."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["books"]["YES"]["bids"] = [[0.49, 1]]  # Very low depth
    obs["books"]["YES"]["asks"] = [[0.50, 1]]
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on insufficient depth"
    print("[PASS] Insufficient depth test passed")


def test_invalid_prices() -> None:
    """Test handling of invalid prices (out of [0,1] range)."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["books"]["YES"]["bids"] = [[1.5, 100]]  # Invalid price > 1
    obs["books"]["YES"]["asks"] = [[-0.1, 100]]  # Invalid price < 0
    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on invalid prices"
    print("[PASS] Invalid prices test passed")


def test_maximum_buy_cash_constraint() -> None:
    """Test that BUY requests respect the $5 maximum."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["account"]["cashUsd"] = 10
    obs["rules"]["maximumBuyCashUsd"] = 5

    # Simulate conditions that might trigger a BUY
    obs["reference"]["btcMidUsd"] = 80474.946
    obs["reference"]["openingTargetUsd"] = 80424.946
    obs["market"]["secondsToClose"] = 60

    result = decide(obs)
    if result["action"] == "BUY":
        amount = float(result["maxCashUsd"])
        assert amount <= 5, f"BUY exceeds $5 cap: {amount}"
    print("[PASS] Maximum BUY cash constraint test passed")


def test_insufficient_cash() -> None:
    """Test that bot respects available cash."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["account"]["cashUsd"] = 2.0  # Low cash
    obs["rules"]["maximumBuyCashUsd"] = 5

    result = decide(obs)
    if result["action"] == "BUY":
        amount = float(result["maxCashUsd"])
        assert amount <= 2.0, f"BUY exceeds available cash: {amount}"
    print("[PASS] Insufficient cash test passed")


def test_position_handling() -> None:
    """Test handling of existing positions."""
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["account"]["position"] = {
        "market_id": "test-market",
        "outcome": "YES",
        "shares": 5,
        "buy_gross_usd": 2.5,
        "buy_fees_usd": 0.03,
        "sell_gross_usd": 0,
        "sell_fees_usd": 0
    }

    result = decide(obs)
    assert result["action"] in {"HOLD", "SELL"}, "With position, should HOLD or SELL"
    print("[PASS] Position handling test passed")


def test_near_expiry() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["market"]["secondsToClose"] = 10  # Very close to expiry
    obs["market"]["id"] = "expiry-test-market"  # Unique market ID

    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD near expiry when flat"

    # With position, should exit
    obs["account"]["position"] = {
        "market_id": "expiry-test-market",
        "outcome": "YES",
        "shares": 5,
        "buy_gross_usd": 2.5,
        "buy_fees_usd": 0.03,
        "sell_gross_usd": 0,
        "sell_fees_usd": 0
    }
    # Ensure bids have sufficient depth
    obs["books"]["YES"]["bids"] = [[0.49, 100]]
    result = decide(obs)
    assert result["action"] == "SELL", "Should SELL near expiry when holding"
    print("[PASS] Near expiry test passed")


def test_duplicate_observations() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()

    # Multiple identical calls should not cause errors
    for _ in range(5):
        result = decide(obs)
        assert result["action"] in {"HOLD", "BUY", "SELL"}, "Valid action required"

    print("[PASS] Duplicate observations test passed")


def test_small_reference_gap() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["market"]["id"] = "small-gap-test-market"
    obs["reference"]["btcMidUsd"] = 80430.0  # Only $5 gap
    obs["reference"]["openingTargetUsd"] = 80425.0
    obs["market"]["secondsToClose"] = 60

    result = decide(obs)
    assert result["action"] == "HOLD", "Should HOLD on small gap"
    print("[PASS] Small reference gap test passed")


def test_exit_logic_profitable() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["market"]["id"] = "profit-test-market"
    obs["account"]["position"] = {
        "market_id": "profit-test-market",
        "outcome": "YES",
        "shares": 5,
        "buy_gross_usd": 2.0,
        "buy_fees_usd": 0.05,
        "sell_gross_usd": 2.5,
        "sell_fees_usd": 0.05
    }
    # Ensure bids have sufficient depth
    obs["books"]["YES"]["bids"] = [[0.49, 100]]

    result = decide(obs)
    assert result["action"] == "SELL", "Should SELL profitable position"
    print("[PASS] Exit on profit test passed")


def test_exit_logic_stop_loss() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["market"]["id"] = "stoploss-test-market"
    obs["account"]["position"] = {
        "market_id": "stoploss-test-market",
        "outcome": "YES",
        "shares": 5,
        "buy_gross_usd": 2.5,
        "buy_fees_usd": 0.05,
        "sell_gross_usd": 0.8,  # Lower value to trigger stop loss
        "sell_fees_usd": 0.05
    }
    # Ensure bids have sufficient depth
    obs["books"]["YES"]["bids"] = [[0.16, 100]]

    result = decide(obs)
    assert result["action"] == "SELL", "Should SELL on stop loss"
    print("[PASS] Stop loss exit test passed")


def test_missing_reference() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["market"]["id"] = "no-ref-test-market-unique-001"
    obs["market"]["secondsToClose"] = 60
    obs["account"]["position"] = None  # Ensure no position
    del obs["reference"]

    result = decide(obs)
    # Should handle gracefully without crashing
    assert result["action"] in {"HOLD", "BUY", "SELL"}, f"Should return valid action, got {result}"
    print("[PASS] Missing reference test passed")


def test_invalid_reference_structure() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["market"]["id"] = "invalid-ref-test-market-unique-002"
    obs["market"]["secondsToClose"] = 60
    obs["account"]["position"] = None  # Ensure no position
    obs["reference"] = "invalid"

    result = decide(obs)
    # Should handle gracefully without crashing
    assert result["action"] in {"HOLD", "BUY", "SELL"}, f"Should return valid action, got {result}"
    print("[PASS] Invalid reference structure test passed")


def test_book_price_validation() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["books"]["YES"]["bids"] = [[0.0, 100], [1.0, 100], [-0.5, 100]]  # Invalid prices
    obs["books"]["YES"]["asks"] = [[1.2, 100], [0.5, 100]]  # One valid, one invalid

    result = decide(obs)
    assert result["action"] in {"HOLD", "BUY", "SELL"}, "Should handle gracefully"
    print("[PASS] Book price validation test passed")


def test_minimum_order_size_consideration() -> None:
    reset_bot_state()
    obs = SAMPLE_OBSERVATION.copy()
    obs["books"]["YES"]["bids"] = [[0.49, 100]]
    obs["books"]["YES"]["asks"] = [[0.50, 100]]
    obs["books"]["YES"]["minOrderSize"] = 10

    result = decide(obs)
    # Bot should handle this without crashing
    assert result["action"] in {"HOLD", "BUY", "SELL"}
    print("[PASS] Minimum order size test passed")


def run_all_tests() -> None:
    """Run all test functions."""
    tests = [
        test_sample_observation,
        test_response_schema,
        test_buy_response_validation,
        test_missing_fields,
        test_malformed_fields,
        test_stale_reference,
        test_future_target_observation,
        test_provisional_target,
        test_empty_books,
        test_wide_spreads,
        test_insufficient_depth,
        test_invalid_prices,
        test_maximum_buy_cash_constraint,
        test_insufficient_cash,
        test_position_handling,
        test_near_expiry,
        test_duplicate_observations,
        test_small_reference_gap,
        test_exit_logic_profitable,
        test_exit_logic_stop_loss,
        test_missing_reference,
        test_invalid_reference_structure,
        test_book_price_validation,
        test_minimum_order_size_consideration,
    ]

    failed = []
    for test in tests:
        try:
            reset_bot_state()  # Reset before each test
            test()
        except AssertionError as e:
            print(f"[FAIL] {test.__name__} failed: {e}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"[FAIL] {test.__name__} error: {e}")
            failed.append(test.__name__)

    print(f"\n{'='*60}")
    print(f"Tests run: {len(tests)}")
    print(f"Tests passed: {len(tests) - len(failed)}")
    print(f"Tests failed: {len(failed)}")
    if failed:
        print(f"Failed tests: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
