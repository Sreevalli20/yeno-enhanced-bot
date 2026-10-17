#!/usr/bin/env python3
"""Tests for the web interface including homepage, health check, and decision endpoint.

Note: This test requires the bot server to be running on http://127.0.0.1:8080
Start the server in a separate terminal before running these tests:
    python yeno_competition_starter_bot.py
"""

from __future__ import annotations

import json
import sys
import urllib.request


# Sample observation for testing
SAMPLE_OBSERVATION = {
    "schemaVersion": 1,
    "timestamp": 1789880823.619,
    "market": {
        "id": "test-market",
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


BASE_URL = "http://127.0.0.1:8080"


def test_homepage() -> None:
    """Test that the homepage returns HTML with expected content."""
    request = urllib.request.Request(f"{BASE_URL}/", method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        html = response.read().decode("utf-8")

    assert "YeNo Enhanced Bot" in html, "Homepage should contain title"
    assert "Paper Trading Research" in html, "Homepage should mention paper trading"
    assert "IMPORTANT DISCLAIMER" in html, "Homepage should have disclaimer"
    assert "paper-trading research bot" in html, "Homepage should explain it's a research bot"
    assert "does NOT execute real trades" in html, "Homepage should state no real trades"
    assert "Run Analysis" in html, "Homepage should have analysis button"
    assert "Load Sample Data" in html, "Homepage should have sample data button"
    assert "GET /health" in html, "Homepage should document health endpoint"
    assert "POST /decide" in html, "Homepage should document decide endpoint"
    print("[PASS] Homepage test passed")


def test_health_check() -> None:
    """Test that /health returns correct JSON response."""
    request = urllib.request.Request(f"{BASE_URL}/health", method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        data = json.loads(response.read())

    assert data == {"status": "healthy"}, f"Health check failed: {data}"
    print("[PASS] Health check test passed")


def test_decide_endpoint() -> None:
    """Test that /decide endpoint returns valid decision."""
    request = urllib.request.Request(
        f"{BASE_URL}/decide",
        method="POST",
        data=json.dumps(SAMPLE_OBSERVATION).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        decision = json.loads(response.read())

    assert isinstance(decision, dict), "Decision must be a dict"
    assert "action" in decision, "Decision must have 'action' field"
    assert decision["action"] in {"HOLD", "BUY", "SELL"}, f"Invalid action: {decision['action']}"
    if decision["action"] == "BUY":
        assert "outcome" in decision, "BUY must have 'outcome'"
        assert decision["outcome"] in {"YES", "NO"}, f"Invalid outcome: {decision['outcome']}"
        assert "maxCashUsd" in decision, "BUY must have 'maxCashUsd'"
        amount = float(decision["maxCashUsd"])
        assert 0 < amount <= 5, f"BUY exceeds $5 cap: {amount}"
    print("[PASS] Decide endpoint test passed")


def test_404_on_invalid_path() -> None:
    """Test that invalid paths return 404."""
    try:
        request = urllib.request.Request(f"{BASE_URL}/invalid", method="GET")
        urllib.request.urlopen(request, timeout=5)
        assert False, "Should have returned 404"
    except urllib.error.HTTPError as e:
        assert e.code == 404, f"Expected 404, got {e.code}"
    print("[PASS] 404 test passed")


def test_decide_with_missing_fields() -> None:
    """Test that /decide handles missing fields gracefully."""
    invalid_obs = {"invalid": "data"}
    request = urllib.request.Request(
        f"{BASE_URL}/decide",
        method="POST",
        data=json.dumps(invalid_obs).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        decision = json.loads(response.read())

    assert decision["action"] == "HOLD", "Should HOLD on invalid input"
    print("[PASS] Missing fields test passed")


def test_decide_content_type() -> None:
    """Test that /decide returns correct content type."""
    request = urllib.request.Request(
        f"{BASE_URL}/decide",
        method="POST",
        data=json.dumps(SAMPLE_OBSERVATION).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        content_type = response.headers.get("Content-Type", "")

    assert "application/json" in content_type, f"Wrong content type: {content_type}"
    print("[PASS] Content type test passed")


def test_homepage_content_type() -> None:
    """Test that homepage returns HTML content type."""
    request = urllib.request.Request(f"{BASE_URL}/", method="GET")
    with urllib.request.urlopen(request, timeout=5) as response:
        content_type = response.headers.get("Content-Type", "")

    assert "text/html" in content_type, f"Wrong content type: {content_type}"
    print("[PASS] Homepage content type test passed")


def run_all_tests() -> None:
    """Run all web interface tests."""
    print("Starting web interface tests...")
    print(f"Testing against {BASE_URL}")
    print("Make sure the bot server is running on that URL.")
    print()

    tests = [
        test_homepage,
        test_homepage_content_type,
        test_health_check,
        test_decide_endpoint,
        test_decide_content_type,
        test_404_on_invalid_path,
        test_decide_with_missing_fields,
    ]

    failed = []
    for test in tests:
        try:
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
        print("All web interface tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
