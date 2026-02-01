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

## Test Tracking (CRITICAL)

**Keep record of all tested spreads using the parser:**

```bash
# After each backtest completes, parse to CSV:
~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\parse_report.py \
    output/report.htm --output mt4_bt_log.csv
```

**Rules:**
- **NEVER RE-test a spread that is already tested in full period**
- Each test adds one row to the CSV with full results

---

## Part 1: QC Sweep (Quality Control)

**Spreads to test:** 1, 10, 20, 30

**Date range:** FULL PERIOD (2000.01.01 to today) **unless user requested otherwise**

**Purpose:** Get baseline performance data and identify which spreads PASS/FAIL.

---

## Part 2: Lower Boundary Search

**Trigger:** Spread 1 FAILS in QC sweep

**Method:**
1. Extract FIRST SL date from s1 FAIL test
2. Define focus range: 4 months BEFORE to 1 month AFTER that SL date
3. Binary search between 1 (FAIL) and lowest PASS from QC
4. **Use FOCUSED RANGE for all binary search tests** (NOT full period)

**Date range:** FOCUSED RANGE around SL date from s1 FAIL test

**⚠️ DO NOT re-test s1** - it was already tested in QC sweep with CSV logged.

**Output:** Minimum spread where EA passes (0 SL)

---

## Part 3: Upper Boundary Search (with SL Date Range Optimization)

**Trigger:** Need to find maximum spread that passes

### Step A: Determine Search Range

**CRITICAL:** Check QC sweep results FIRST before testing s50.

| QC Result | Action |
|-----------|--------|
| **s30 FAILS** | Extract SL dates from s30 test. Binary search with FOCUSED RANGE between s20 (PASS) and s30. |
| **s30 PASSES** | Test s50 (full period) to find where it eventually fails. |

**⚠️ IMPORTANT:**
- When QC spread FAILS (s1 or s30), extract SL dates from that FAIL test
- Use those SL dates for FOCUSED RANGE in binary search
- **DO NOT use full period for binary search after QC FAIL is found**
- **DO NOT re-test any spread that was already tested in QC sweep**

**Examples:**
- `s20 PASS, s30 FAIL` → Extract SL dates from s30 test → Focused range binary search [20, 30] → **DO NOT re-test s20 or s30**
- `s20 PASS, s30 PASS` → Test s50 (full period) → if fails, extract SL dates → Focused range binary search
- `s1 FAILS, s10 PASSES` → Extract SL dates from s1 test → Focused range binary search [1, 10] (see Part 2)

### Step B: Binary Search with Focused Range

**APPLIES TO BOTH UPPER AND LOWER BOUNDARY SEARCHES**

For each SL date found in the FAIL test:

1. **Define focus range:** 4 months BEFORE to 1 month AFTER that SL date
   - Example: SL on 2025.01.05 → test range [2024.09.05 to 2025.02.05]
   - Use the FIRST SL date if multiple exist

2. Binary search between known PASS and FAIL within this focused range

3. Find boundary for this specific SL date

**NOTE:** Only full period tests are:
- Initial QC sweep (s1, s10, s20, s30)
- Optional s50 test (if all QC pass)
- Final validation test

**All binary searches use FOCUSED RANGE around SL dates.**

### Step C: Test Boundary Against Subsequent SL Dates

**⚠️ SKIP if boundary is from QC sweep (s1, s10, s20, s30) - those were already FULL PERIOD tested.**

Once boundary found for 1st SL date:

1. Test that boundary against 2nd SL date range (4 months before to 1 month after)
2. If PASSES → boundary sustains, proceed to 3rd SL date
3. If FAILS → new, lower boundary from 2nd SL date overrides
4. Repeat for all SL dates found in original FAIL test

### Step D: Final Validation

**⚠️ SKIP if boundary is from QC sweep (s1, s10, s20, s30) - those were already FULL PERIOD tested.**

Run full period backtest with final upper boundary to confirm 0 SL across entire history.

**Date range:** FULL PERIOD (2000.01.01 to today) unless user requested otherwise

---

## Binary Search Algorithm (Detailed)

Given: PASS at spread X, FAIL at spread Y

**All tests use FOCUSED RANGE (4M before to 1M after SL date) unless specified.**

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

### Example (with FOCUSED RANGE)

- s30 PASS, s50 FAIL → SL date from s50: 2009.12.31 03:02
- Focused range: [2009.08.31 to 2010.01.31]
- Midpoint = 40 → test s40 on focused range
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

- ⚠️ **ALL tests must use `--output mt4_bt_log.csv`** to log results
- **DO NOT re-test any spread that was already tested** (check CSV log)
- All full period tests use `--timeout 7200` (2 hours) due to TDS data initialization
- Focused range tests (4M before, 1M after SL date) are faster and save time during boundary search
- Always parse results with `parse_report.py` after each backtest to verify SL status
- Original `.set` files in `sets/` folder are never modified
