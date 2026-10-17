# YeNo × Builderr Volume Bot Challenge - Enhanced Submission

**Bot Name:** Enhanced Volume Bot v1

**Python Version:** 3.14+ (uses standard library only)

## Overview

This is an enhanced trading bot for the YeNo × Builderr $500 Volume Bot Challenge. The bot implements an evidence-based strategy with adaptive position sizing, spread analysis, depth requirements, and imbalance detection while maintaining strict compliance with the official evaluator contract.

## Quick Start

### Local Development

1. Ensure Python 3.14+ is installed:
```bash
python --version
```

2. Start the bot:
```bash
python yeno_competition_starter_bot.py
```

The bot will start on `http://127.0.0.1:8080` by default.

3. Test with the official smoke test (in a separate terminal):
```bash
python yeno-smoke-test.py
```

Expected output:
```json
{
  "contractSmokePassed": true,
  "decision": {
    "action": "BUY",
    "outcome": "YES",
    "maxCashUsd": 2.6125
  }
}
```

### Environment Variables

- `PORT`: Server port (default: 8080)
- `HOST`: Server host (default: 127.0.0.1 for local, 0.0.0.0 for production)

Example:
```bash
PORT=8080 HOST=0.0.0.0 python yeno_competition_starter_bot.py
```

## API Endpoints

### POST /decide

Official competition endpoint for trading decisions.

**Request:** JSON observation (see `yeno-sample-observation.json` for example)

**Response:** JSON decision
```json
{"action":"HOLD"}
{"action":"BUY","outcome":"YES","maxCashUsd":5}
{"action":"SELL"}
```

### GET /health

Health check endpoint for deployment monitoring.

**Response:**
```json
{"status":"healthy"}
```

## Testing

### Run Automated Tests

```bash
python test_enhanced_bot.py
```

All 24 tests cover:
- Official sample observation validation
- Response schema compliance
- Missing and malformed field handling
- Stale and invalid reference rejection
- Empty books, wide spreads, insufficient depth
- Invalid price handling
- Maximum BUY cash constraint
- Position handling and exit logic
- Near expiry behavior
- Duplicate observations
- Small reference gap rejection
- Profit and stop-loss exit triggers

### Test Results

```
Tests run: 24
Tests passed: 24
Tests failed: 0
All tests passed!
```

**Final Verification (2026-10-17):**
- Python version: 3.14.6
- Automated tests: 24/24 PASSED
- Smoke test: PASSED (contractSmokePassed: true)
- Local server health check: PASSED
- Local /decide endpoint: PASSED
- Contract compliance: VERIFIED (including 15s no-entry zone)
- Git commit: 890e94154ae1676fb6d41393a4477dfad606c27e

## Strategy Improvements

This bot enhances the House Bot v1 baseline with:

1. **Adaptive Position Sizing**: Scales 0.5x to 1.2x based on remaining cash, historical PnL, and drawdown
2. **Expanded Trading Window**: 105-second window (120s entry - 15s exit) for more opportunities
3. **Spread Analysis**: Rejects markets with spread > 8% of midpoint
4. **Depth Requirements**: Minimum $2.50 depth on both bid/ask sides
5. **Imbalance Detection**: Aligns trades with order flow using bid/ask imbalance
6. **Relaxed Entry Filters**: $30 reference gap (vs $50), 0.92 price ceiling (vs 0.90)
7. **Increased Cycle Limit**: 3 cycles per market (vs 2)
8. **Enhanced Risk Management**: Adaptive stop loss, immediate roundtrip loss limit, PnL-based sizing
9. **Robust Error Handling**: Comprehensive input validation and graceful degradation

See `STRATEGY_COMPARISON.md` for detailed comparison with House Bot v1.

## Contract Compliance

The bot strictly adheres to all official evaluator contract requirements:

- $10 starting simulated cash
- $5 maximum fee-inclusive BUY
- 24-hour evaluation window
- $1,000 eligible volume target
- One position or pending BUY at a time
- BTC five-minute Up/Down markets only
- Terminal-flat finish with no pending action
- 200ms response deadline
- Polymarket dynamic fee calculation
- YeNo 1% overlay fee
- 15-second no-entry zone before expiry

See `yeno-evaluator-contract.md` for the complete official contract.

## Render Deployment

### Prerequisites

- GitHub account with the repository uploaded
- Render account (free tier sufficient)

### Deployment Steps

1. **Push your code to GitHub:**
   - Create a new repository on GitHub
   - Upload all files from this project
   - Commit and push

2. **Create Render Web Service:**
   - Log in to [Render](https://render.com)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect `render.yaml` configuration

3. **Verify Settings:**
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python yeno_competition_starter_bot.py`
   - Health Check Path: `/health`
   - Environment Variables:
     - `PORT`: 10000 (or leave as configured in render.yaml)
     - `HOST`: 0.0.0.0

4. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment to complete (usually 1-2 minutes)
   - Render will provide a live HTTPS URL

5. **Test Live Endpoint:**
   ```bash
   # Test health check
   curl https://your-app.onrender.com/health

   # Test /decide endpoint
   curl -X POST https://your-app.onrender.com/decide \
     -H "Content-Type: application/json" \
     -d @yeno-sample-observation.json
   ```

### Troubleshooting

- Check Render logs for startup errors
- Ensure `PORT` and `HOST` environment variables are set
- Verify the bot listens on `0.0.0.0` (not `127.0.0.1`) for production
- Health check should return `{"status":"healthy"}`

## Project Structure

```
yeno-starter-kit/
├── yeno_competition_starter_bot.py  # Main bot implementation
├── test_enhanced_bot.py              # Comprehensive test suite
├── yeno-smoke-test.py                # Official smoke test
├── yeno-sample-observation.json      # Official sample observation
├── yeno-house-bot-v1.py             # Baseline reference bot
├── yeno-house-bot-configs.json       # Baseline configurations
├── yeno-evaluator-contract.md        # Official contract documentation
├── yeno-house-bot-benchmark.md       # Official benchmark results
├── yeno-starter-readme.md            # Original starter kit readme
├── STRATEGY_COMPARISON.md            # Detailed strategy comparison
├── requirements.txt                  # Dependencies (none required)
├── render.yaml                       # Render deployment configuration
├── .gitignore                        # Git ignore rules
└── README.md                         # This file
```

## Dependencies

**None** - This project uses only Python 3.14 standard library.

No external packages, API keys, or databases required.

## Important Limitations

1. **No Historical Data**: The starter kit does not include the 30-path development diagnostic dataset, so no quantitative backtesting is possible.

2. **No Official Evaluator Access**: The bot cannot be tested against the actual 24-hour forward evaluation environment.

3. **Theoretical Improvements**: Performance gains are theoretical based on baseline analysis; actual qualification depends on unseen forward data.

4. **Signal Quality**: The bot relies primarily on the BTC reference signal; no additional predictive features are available.

5. **Execution Assumptions**: The bot assumes the evaluator's 250ms execution latency as documented; actual fill quality may vary.

## Submission Information

### Builderr Competition Submission

Email: `submit@builderr.ai`

Include:
- Bot name: "Enhanced Volume Bot v1"
- Contact: your email address
- Repository URL: your GitHub repository URL
- Immutable commit SHA: (after final commit)
- HTTPS endpoint: your Render deployment URL (if deployed)
- Container digest: N/A (not using containers)

### Git Commit

After finalizing changes:
```bash
git add .
git commit -m "Final submission: Render-ready enhanced YeNo bot"
git rev-parse HEAD  # Copy the SHA for submission
```

## Honest Assessment

This implementation is a realistically defensible improvement over the House Bot v1 baseline based on:
- Documented baseline limitations (best path: $942.59, median: $558.83)
- Evidentiary improvements (adaptive sizing, spread/depth/imbalance filters)
- Strict contract compliance
- Comprehensive testing

**However, I cannot guarantee first place, qualification, or any specific performance metric.** The starter kit lacks historical data for backtesting, and the official evaluation uses unseen forward data. The improvements are theoretical and must be validated by the official evaluator.

Passing the smoke test and automated tests proves **contract compliance** and correct response schema. It does **not** guarantee qualification or any specific outcome in the official 24-hour evaluation.

## License

This submission is for the YeNo × Builderr Volume Bot Challenge. All original competition files remain under their respective licenses.

## Support

For competition-specific questions, refer to:
- Official contract: `yeno-evaluator-contract.md`
- Official benchmark: `yeno-house-bot-benchmark.md`
- Competition contact: Builderr via `submit@builderr.ai`
