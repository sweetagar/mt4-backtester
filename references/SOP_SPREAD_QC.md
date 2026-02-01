---
keywords: [QC, Spread Sweep, Spread Boundary, Boundary Search]
related: [mt4_runner.py, parse_report.py]
---

# SOP: Spread Boundary Search (QC)

**Purpose:** Find the minimum and maximum spread values where an EA parameter set produces 0 SL (Stop Loss) across full period testing.

**Activation Keywords:** QC, Spread Sweep, Spread Boundary, Boundary Search

---

## Pass/Fail Criteria

- **PASS** = 0 SL (empty `sl_date` field in parsed CSV)
- **FAIL** = At least 1 SL (has entries in `sl_date` field)

---

## Part 1: QC Sweep (Quality Control)

**Spreads to test:** 1, 10, 20, 30

**Date range:** FULL PERIOD (2000.01.01 to today) **unless user requested otherwise**

**Purpose:** Get baseline performance data and identify which spreads PASS/FAIL.

---

## Part 2: Lower Boundary Search

**Trigger:** Spread 1 FAILS in QC sweep

**Method:** Binary search between 1 (FAIL) and lowest PASS from QC

**Date range:** FULL PERIOD (2000.01.01 to today) unless user requested otherwise

**Output:** Minimum spread where EA passes (0 SL)

---

## Part 3: Upper Boundary Search (with SL Date Range Optimization)

**Trigger:** Need to find maximum spread that passes (all QC pass or user wants higher)

### Step A: Find Initial FAIL

1. Test spread 50 (full period)
2. If s50 PASSES → test higher (s75, s100...) until FAIL found
3. If s50 FAILS → proceed with s30(PASS) and s50(FAIL) as boundaries

### Step B: Binary Search Per SL Date

For each SL date found in the FAIL test:

1. **Define focus range:** 4 months BEFORE to 1 month AFTER that SL date
   - Example: SL on 2025.01.05 → test range [2024.09.05 to 2025.02.05]
   - Use the FIRST SL date if multiple exist

2. Binary search between known PASS and FAIL within this focused range

3. Find boundary for this specific SL date

### Step C: Test Boundary Against Subsequent SL Dates

Once boundary found for 1st SL date:

1. Test that boundary against 2nd SL date range (4 months before to 1 month after)
2. If PASSES → boundary sustains, proceed to 3rd SL date
3. If FAILS → new, lower boundary from 2nd SL date overrides
4. Repeat for all SL dates found in original FAIL test

### Step D: Final Validation

Run full period backtest with final upper boundary to confirm 0 SL across entire history.

**Date range:** FULL PERIOD (2000.01.01 to today) unless user requested otherwise

---

## Binary Search Algorithm (Detailed)

Given: PASS at spread X, FAIL at spread Y

1. Calculate midpoint = round((X + Y) / 2)
2. Test midpoint spread
3. If midpoint FAILS:
   - New range: [X, midpoint]
   - Y = midpoint
4. If midpoint PASSES:
   - New range: [midpoint, Y]
   - X = midpoint
5. Repeat until (Y - X) = 1
6. Final boundary: X (last known PASS)

### Example

- s30 PASS, s50 FAIL
- Midpoint = 40 → test s40
- If s40 FAILS: range [30, 40], midpoint = 35
- If s35 PASSES: range [35, 40], midpoint = 37
- If s37 FAILS: range [35, 37], midpoint = 36
- If s36 PASSES: range [36, 37] → STOP
- Final boundary: 36

---

## Final Output

Report the spread range where EA passes (0 SL):

```
Spread Boundary: [min_pass, max_pass]
Example: [8, 36] = EA has 0 SL from spread 8 to spread 36
```

---

## Notes

- All full period tests use `--timeout 7200` (2 hours) due to TDS data initialization
- Focused range tests (4M before, 1M after SL date) are faster and save time during boundary search
- Always parse results with `parse_report.py` after each backtest to verify SL status
- Original `.set` files in `sets/` folder are never modified
