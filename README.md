# MT4 Backtester (AI AGENT SKILL)

Python-based automation system for MT4 (MetaTrader 4) backtesting workflows. Enables AI Agents (like Claude Code & Opencode) to help automate backtesting, quality control, and optimization.

---

## Features

- **Single & Parallel Backtesting** - Run multiple tests across MT4 terminals
- **Quality Control (QC)** - Spread boundary testing
- **SL Hunting** - Parameter refinement to avoid stop losses
- **Report Parsing** - Extract 21 metrics from MT4 HTML reports to CSV
- **AI Agent Support** - Claude Code and Opencode Compatible

## Sample Prompts
```
/mt4-backtester all AUDNZD sets with My_EA_v1.2 over 2025 to 2026 using spread 10, 20, 30

/mt4-backtester EURUSD_Avd_EA.set, EA: Adv_EA Version 2.0, spread 15, full period
```

## Sample Output
```
All 6 backtests completed successfully!

┌──────────┬────────┬────────────┬───────────┬──────────┬────────┬─────────┐
│ Set      │ Spread │ Net Profit │ MDD       │ PM_Ratio │ Trades │ Cycles  │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ Set_1    │ 10     │ 2341.50    │ -412.30   │ 5.68     │ 423    │ 87      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ Set_1    │ 20     │ 1876.20    │ -398.45   │ 4.71     │ 389    │ 76      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ Set_1    │ 30     │ 1054.80    │ -521.67   │ 2.02     │ 312    │ 58      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ Set_2    │ 10     │ 3521.90    │ -287.12   │ 12.27    │ 567    │ 124     │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ Set_2    │ 20     │ 2987.40    │ -298.56   │ 10.01    │ 498    │ 98      │
├──────────┼────────┼────────────┼───────────┼──────────┼────────┼─────────┤
│ Set_2    │ 30     │ 1654.30    │ -445.78   │ 3.71     │ 421    │ 71      │
└──────────┴────────┴────────────┴───────────┴──────────┴────────┴─────────┘
```

---

## Installation

### Quick Install (Recommended)

Run the automated installer from this project folder:

```cmd
cd C:\Users\UserName\dev\mt4-backtester
install_skill.bat
```

The installer will:
- Copy skill files to your chosen location (Claude Code / OpenCode / Both)
- Create Python virtual environment (`.venv`)
- Install all required dependencies

Follow the on-screen prompts to complete installation.

---

### Manual Install

If you prefer manual installation:

**Step 1: Copy Skill to Skills/ Folder**

Copy the skill folder structure to your Claude skills directory:

```
~\.claude\skills\mt4-backtester\
├── SKILL.md
├── requirements.txt
├── references\
│   └── SOP_SPREAD_QC.md
└── scripts\
    ├── mt4_runner.py
    └── parse_report.py
```

**For Claude Code:** `C:\Users\YourUsername\.claude\skills\mt4-backtester\`

**For OpenCode:** `C:\Users\YourUsername\.config\opencode\skills\mt4-backtester\`

**Step 2: Create Python Virtual Environment**

```cmd
cd C:\Users\YourUsername\.claude\skills\mt4-backtester
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

---

## OpenCode Users (Background Tasks Support)

If using **OpenCode**, background tasks require additional configuration.

### Enable Background Plugin

Add to `C:\Users\YourUsername\.config\opencode\config.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["@zenobius/opencode-background"]
}
```

This enables the background task feature needed for parallel testing.

---

## Project Setup

### 1. Create `.env` File

In your working directory (where you'll run backtests), create `.env`:

```ini
# MT4 Terminals
mt4-01=C:\path\to\mt4-01\terminal.exe
mt4-02=C:\path\to\mt4-02\terminal.exe
mt4-03=C:\path\to\mt4-03\terminal.exe
mt4-04=C:\path\to\mt4-04\terminal.exe

# Output directories
mt4_bt_output=.\output
mt4_bt_ini=.\configs
mt4_bt_sets=.\sets

# EA spread parameters (for auto-adjustment)
mt4_spread_params=entry_max_spread_allowed_in_points,exit_max_spread_allowed_in_points
```

### 2. Directory Structure

```
your-project/
├── .env
├── sets/              # EA .set files (master copies)
├── output/            # HTML reports from MT4
├── configs/           # Generated INI files
└── mt4/               # MT4 sandbox terminals
    ├── mt4-01/
    │   ├── terminal.exe
    │   ├── MQL4/Experts/
    │   ├── tester/
    │   └── config/tds.config
    └── mt4-02/
```

---

## Quick Start

Ask AI Agent to run a backtest:

```
"Run backtest with my_ea_param.set, full period, timeframe M5"
```

AI Agent will:
1. Gather missing parameters (symbol, date range, which EA)
2. Generate INI file
3. Run MT4 backtest
4. Parse results to CSV

---

## Documentation For Human Usage

- **scripts/README.md** - Script usage and examples

---

## Requirements

- Python 3.7+
- MT4 Terminal(s) with Tick Data Suite (TDS)
- Dependencies in `requirements.txt`:
  - python-dotenv
  - pandas
  - lxml
  - openpyxl

---

## License

MIT
