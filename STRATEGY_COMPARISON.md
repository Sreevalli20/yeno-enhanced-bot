# Enhanced Bot vs House Bot v1 Comparison

## Key Improvements

### 1. Adaptive Position Sizing
- **House Bot v1**: Fixed 5 shares per entry
- **Enhanced Bot**: Scales position size based on:
  - Remaining cash
  - Historical PnL performance
  - Drawdown levels
  - Base shares adjusted 0.5x to 1.2x based on conditions

### 2. Expanded Trading Window
- **House Bot v1**: 75-second window (90s entry - 15s forced exit)
- **Enhanced Bot**: 105-second window (120s entry - 15s forced exit)
  - Allows more opportunities while maintaining safe exit margin
  - Both respect the 15-second no-entry zone before expiry

### 3. Spread Analysis
- **House Bot v1**: No spread filtering
- **Enhanced Bot**: Rejects markets with spread > 8% of midpoint
  - Avoids adverse execution in illiquid conditions

### 4. Depth Requirements
- **House Bot v1**: Checks immediate exit depth for target shares only
- **Enhanced Bot**: Requires minimum depth thresholds:
  - Ask depth >= $2.50 USD
  - Bid depth >= $2.50 USD
  - Ensures executable liquidity

### 5. Imbalance Detection
- **House Bot v1**: No imbalance analysis
- **Enhanced Bot**: Calculates bid/ask imbalance and rejects when:
  - Trading YES but bids favored (imbalance < -30%)
  - Trading NO but asks favored (imbalance > +30%)
  - Aligns trades with order flow

### 6. Relaxed Entry Filters
- **House Bot v1**: MINIMUM_REFERENCE_GAP_USD = $50
- **Enhanced Bot**: MINIMUM_REFERENCE_GAP_USD = $30
  - Captures more valid opportunities
  - Compensated by other quality filters

### 7. Relaxed Price Threshold
- **House Bot v1**: MAXIMUM_ENTRY_PRICE = 0.90
- **Enhanced Bot**: MAXIMUM_ENTRY_PRICE = 0.92
  - Allows entries on slightly higher-probability outcomes
  - Still maintains conservative ceiling

### 8. Increased Cycle Limit
- **House Bot v1**: MAXIMUM_CYCLES_PER_MARKET = 2
- **Enhanced Bot**: MAXIMUM_CYCLES_PER_MARKET = 3
  - More volume generation per market
  - Controlled by other risk filters

### 9. Enhanced Risk Management
- **House Bot v1**: Fixed stop loss per share ($0.10)
- **Enhanced Bot**: Adaptive stop loss ($0.15) with:
  - Total PnL tracking
  - Sizing adjustments based on performance
  - Immediate roundtrip loss limit ($0.50)

### 10. Robust Error Handling
- **House Bot v1**: Basic try-catch with HOLD fallback
- **Enhanced Bot**: Comprehensive input validation:
  - Type checking for all numeric fields
  - Graceful handling of malformed data
  - State management per market
  - Detailed logging (for debugging)

## Shared Characteristics (Contract Compliance)

Both bots maintain:
- $5 maximum fee-inclusive BUY constraint
- One position at a time
- 250ms execution latency assumption
- Polymarket dynamic fee calculation
- YeNo 1% overlay fee
- 15-second no-entry zone before expiry
- Terminal-flat requirement
- Reference data validation (stale, provisional, timestamps)

## Smoke Test Results

Both bots produce identical valid responses on the official sample observation:
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

## Expected Behavioral Differences

The enhanced bot should:
1. Enter more frequently due to wider window and relaxed filters
2. Scale positions more conservatively when underperforming
3. Skip illiquid or wide-spread markets that House Bot v1 might trade
4. Generate more volume through higher cycle limit
5. Exit with tighter time margin (15s vs 60s)
6. Align entries with order flow via imbalance analysis

## Risk Considerations

Enhanced bot risks:
- Wider trading window increases exposure to late moves
- Relaxed filters may increase low-quality entries
- Higher cycle limit could lead to overtrading

Mitigations:
- Spread and depth filters screen low-quality markets
- Imbalance analysis aligns with order flow
- Adaptive sizing reduces exposure when underperforming
- Forced exit still ensures terminal-flat completion

## Performance Limitations

Neither bot has access to:
- Historical replay data (not included in starter kit)
- The official 30-path development diagnostic dataset
- Forward 24-hour evaluation data
- Real-time market feed during official run

Therefore, actual qualification performance cannot be guaranteed. The improvements are theoretical based on the documented baseline limitations and contract constraints.
