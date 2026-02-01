---
name: mt4-backtester
description: Automate MT4 (MetaTrader 4) backtesting workflows including single and parallel backtesting, report parsing, SL Hunting, MDD Date Search, Param QC and Spread Boundary finding.
---

# MT4 Backtester

Python-based automation system for MT4 backtesting workflows.

## Directory Structure

### CWD (Current Working Directory)
The project folder where commands are executed. Contains configuration and data.
***IMPORTANT*** Always first read .env file in CWD to find out where things are!

```
~\My_Projects\mt4-test-folder\          # CWD
├── .env                                # Terminal paths, spread params, output locations
├── sets/                               # EA .set files (master copies) [mt4_bt_sets]
├── output/                             # HTML reports from MT4 [mt4_bt_output]
├── configs/                            # Generated INI files [mt4_bt_ini]
└── mt4/                                # MT4 sandbox terminals
    ├── mt4-01/
    │   ├── terminal.exe
    │   ├── MQL4/Experts/
    │   ├── tester/                    # Runtime .set copies + reports
    │   └── config/tds.config
    └── mt4-02/
```

### Skill Folder
Contains Python scripts.
***IMPORTANT*** Always find the skills Folder and its venv!! for opencode users, replace ~\.claude\skills\ to ~\.config\opencode\skills\ in ALL command calls!!

**Windows paths:**
```
# Claude Code
~\.claude\skills\mt4-backtester\

# OpenCode
~\.config\opencode\skills\mt4-backtester\

# Structure (both)
├── scripts/                           # Python scripts
│   ├── mt4_runner.py                  # Backtest runner
│   └── parse_report.py                # Report parser
├── references/                        # SOP documents (loaded on-demand)
│   └── SOP_SPREAD_QC.md               # Spread Boundary Search & QC workflow
├── requirements.txt                   # Python dependencies
└── SKILL.md
```

## Skill Setup

The skill requires a Python virtual environment. If `.venv/` or `venv/` folder is missing:

```bash
# From skill folder
cd ~\.claude\skills\mt4-backtester
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

**Dependencies** (from requirements.txt):
- python-dotenv - Environment configuration
- pandas - CSV handling
- lxml - HTML parsing
- openpyxl - Excel support

## Quick Start

Run a single backtest and parse results:

```bash
# From CWD, using skill's Python
~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\mt4_runner.py \
    --ea "MyEA.ex4" \
    --set file.set \
    --symbol EURUSD \
    --terminal mt4-01

~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\parse_report.py \
    output/report.htm --output mt4_bt_log.csv
```

## Core Scripts

### mt4_runner.py - Backtest Runner

Three modes: **gen_ini** (generate INI only), **run** (run with existing INI), **full** (generate + run).

**Full mode** (most common):
```bash
~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\mt4_runner.py \
    --terminal mt4-01 \
    --ea "KO\GM(Pro)_V1.33_AlgoX_REAL" \
    --set file.set \
    --symbol EURUSD \
    --period M1 \
    --spread 15 \
    --fromdate "2000.01.01" \
    --todate "2026.01.31" \
    --tickdata-src Dukascopy
```

**Key parameters:**
- `--terminal`: mt4-01/02/03/04 (from .env) or full path
- `--ea`: EA name (use `\` for subdirectories)
- `--set`: Set file name (looks in `sets/` by default) [mt4_bt_sets]
- `--period`: **Always use M1** for backtest data feed
- `--spread`: Fixed spread for backtest
- `--fromdate/--todate`: Date range in YYYY.MM.DD format
- `--tickdata-src`: TDS data source (default: **Dukascopy**)

**Auto spread adjustment**: If test spread >= EA param - 1, automatically adjusts copied set file to `test_spread + 10`. Configured via `mt4_spread_params` in .env.

**Important**: Always use `--timeout 7200` (2 hours) for production. First runs take time for TDS data initialization.

### parse_report.py - Report Parser

Extract 21 metrics from MT4 HTML reports to CSV.

```bash
# Parse single file, print to stdout
~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\parse_report.py \
    output/report.htm

# Append to CSV (creates if not exists)
~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\parse_report.py \
    output/report.htm --output mt4_bt_log.csv

# Parse all .htm files in directory
~\.claude\skills\mt4-backtester\.venv\Scripts\python.exe \
    ~\.claude\skills\mt4-backtester\scripts\parse_report.py \
    output/ --output mt4_bt_log.csv
```

**CSV Schema** (22 columns):
- `magic#`, `set_filename`, `symbol`, `direction`, `start_date`, `end_date`
- `spread`, `day_num`, `net_profit`, `mdd`, `pm_ratio`, `yrly_%`
- `trade_num`, `mthly_trades`, `mdd_date`, `sl_date`, `max_lot`, `max_lvl`, `ea_lvl`
- `dist`, `tp0`, `tp1`

**Multi-value fields**: Use `|` separator (e.g., `mdd_date`, `sl_date`)
- `sl_date` format: `YYYY.MM.DD HH:MM (-loss)` - shows loss amount in parentheses
- Excludes "close at stop" trades from SL dates

## Configuration

### .env File (in CWD)

Required for terminal paths and output locations:

```ini
# MT4 Terminals (mt4-01 through mt4-04)
mt4-01=C:\path\to\mt4-01\terminal.exe
mt4-02=C:\path\to\mt4-02\terminal.exe
mt4-03=C:\path\to\mt4-03\terminal.exe
mt4-04=C:\path\to\mt4-04\terminal.exe

# Backtest output locations
mt4_bt_output=.\output        # HTML reports from MT4
mt4_bt_ini=.\configs          # Generated INI files
mt4_bt_sets=.\sets            # EA .set files (master copies)

# EA spread parameters (for auto-adjustment)
mt4_spread_params=entry_max_spread_allowed_in_points,exit_max_spread_allowed_in_points
```

## How It Works

1. **Command executed from CWD**
2. **Python runs from skill's venv** (absolute path)
3. **Script loads .env from CWD** (via python-dotenv)
4. **Relative paths resolved from CWD**:
   - `sets/` [mt4_bt_sets] - Master .set files
   - `output/` [mt4_bt_output] - HTML reports
   - `configs/` [mt4_bt_ini] - Generated INI files
   - `mt4/` - MT4 terminals

## Workflows

### Single Backtest Workflow
```
1. Ensure .env exists in CWD
2. Run mt4_runner.py (full mode) using skill's Python
3. Parse results with parse_report.py
```

### Parallel Testing

**Terminal Pool Pattern** - Queue tasks and start queued tasks as terminals free up:
***IMPORTANT*** Make Sure MAX terminal background tasks is running until task completed without error
1. Start up to number of terminals in .env (wait/sleep/timeout 3s between each task start)
2. Monitor with TaskOutput - check [EVERY 30s] if any terminal task completes
3. When a terminal completes:
    - Parse (without --output) and verify results
    - If `trade_num = 0` (data not available) or missing report: **rerun on same terminal**
    - Release terminal for next queued task after successful parse
4. Parse (WITH --output) new completed htm report upon completion when waiting for tasks
5. Start new backtround immediately if a task is completed without error, repeat until queue empty

**MAX concurrent tests = Number of terminals in .env** (mt4-XX entries)

#### Always Use this format to Report Current Status While Running Tasks 

```
┌─────────┬──────────┬──────┬────────┬─────────┐
│ Task ID │ Terminal │ Set  │ Spread │ Status  │
├─────────┼──────────┼──────┼────────┼─────────┤
│ b8bda5c │ mt4-01   │ 7150 │ 10     │ Running │
├─────────┼──────────┼──────┼────────┼─────────┤
│ b28813f │ mt4-02   │ 7151 │ 10     │ Running │
├─────────┼──────────┼──────┼────────┼─────────┤
│ bde67e5 │ mt4-03   │ 7152 │ 10     │ Running │
├─────────┼──────────┼──────┼────────┼─────────┤
│ b364fdb │ mt4-04   │ 7150 │ 20     │ Running │
└─────────┴──────────┴──────┴────────┴─────────┘
```

#### Always Use this format to Report Results When All Completed

```
┌──────────┬────────┬────────────┬───────────┬──────────┬────────┬─────────┐
│ Set      │ Spread │ Net Profit │ MDD       │ PM_Ratio │ Trades │ Cycles  │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ 7150     │ 10     │ 15234.50   │ -2341.20  │ 6.51     │ 1234   │ 45      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ 7151     │ 10     │ 8765.30    │ -1234.50  │ 7.10     │ 987    │ 38      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ 7152     │ 10     │ -1234.50   │ -3456.70  │ -0.36    │ 654    │ 28      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ 7150     │ 20     │ 5432.10    │ -1876.30  │ 2.90     │ 876    │ 32      │
└──────────┴────────┴────────────┴───────────┴──────────┴────────┴─────────┘
```

---

## References

| Document | Trigger Keywords | Purpose |
|----------|------------------|---------|
| `references/SOP_SPREAD_QC.md` | QC, Spread Sweep, Spread Boundary, Boundary Search | Find min/max spread where EA produces 0 SL |

When user mentions these keywords, agent should read the referenced SOP document and follow the detailed procedure.

---

## Technical Notes

- **TDS Data Initialization**: First run can take hours for tick data indexing
- **Background Mode**: For production, run mt4_runner.py as background task with long timeout
- **Set File Location**: Set files are copied to terminal's `tester/` folder for the test
- **Report Location**: `tester/reportname.htm` relative to terminal, also copied to `output/` [mt4_bt_output]
- **Spread Params**: Auto-adjustment only modifies COPIED set file, never the original in `sets/`

## Troubleshooting

### "python.exe: command not found" or missing .venv

The virtual environment doesn't exist. Create it:

```bash
# From skill folder
cd ~\.claude\skills\mt4-backtester
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### Alternative: Use system Python

If venv setup fails, use system Python directly (ensure dependencies are installed):

```bash
python ~\.claude\skills\mt4-backtester\scripts\mt4_runner.py ...
```

### TDS Data Source

**Default: Dukascopy** - Always use `--tickdata-src Dukascopy` unless you specifically need another source.

## Agent Interaction Pattern

When user requests a backtest, gather missing parameters using AskUserQuestion Tool:

**IMPORTANT**: Only ask if user did NOT specify. No defaults except technical requirements.

### Required Parameters

| Parameter | Ask If Missing? | Notes |
|-----------|-----------------|-------|
| `--set` | YES | List .set files in `sets/`, user selects |
| `--ea` | YES | List EAs in <terminal_folder in .env>\MQL4\Experts\, user selects |
| `--symbol` | YES | No default - user must specify |
| `--spread` | YES | No default - user must specify |
| `--fromdate/--todate` | YES | No default - "Full Period" = 2000.01.01 to today |
| `--period` | NO | Use M1(unless user specify other wise) |
| `--terminal` | NO | Use first one available |
| `--tickdata-src` | NO | Use Dukascopy(unless user specify other wise) |

### Example Flow

```
User: "Run backtest with 7152_AUDCAD.set"

Agent asks: "Spread value?"
User: "12"

Agent asks: "Date range?"
User: "Full period" → Agent uses 2000.01.01 to today

Agent asks: "Confirm: AUDCAD, spread 12, 2000.01.01-today, mt4-01?"
User: Yes → Run
```

### Post-Test Process (Default Behavior)

**After backtest completes:**

1. **Parse and verify**: If `trade_num = 0` (data not available) or report missing, **rerun the test**
2. **Parse to CSV**: After successful parse, append to `mt4_bt_log.csv` (default behavior unless otherwise requested)
3. **Show results**: Display key metrics from the parsed CSV entry

**Do NOT ask** "Parse to CSV?" - this is automatic by default.
