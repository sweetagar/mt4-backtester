# MT4 Backtester - Scripts Usage

## mt4_runner.py

Core script for running MT4 backtests from command line.

---

## Three Modes

### GEN - Generate INI Only
```bash
python scripts/mt4_runner.py --ea "KO\GM.ex4" --set file.set --symbol EURUSD --output-ini config.ini
```

### RUN - Run with Existing INI
```bash
python scripts/mt4_runner.py --terminal mt4-01 --ini config.ini
```

### FULL - Generate INI + Run
```bash
python scripts/mt4_runner.py --terminal mt4-01 --ea "KO\GM.ex4" --set file.set --symbol EURUSD
```

---

## Path Resolution Rules

### `--report-path`

| Input | Behavior |
|-------|----------|
| Not specified | Uses default: `./results` (or `mt4_bt_output` from .env if exists) |
| Directory only: `"output"` | Uses specified directory, auto-generates filename: `setfile_YYYYMMDD_HHMMSS.htm` |
| Full path with .htm: `"output/myreport.htm"` | Uses specified directory AND exact filename |

### `--set`

| Input | Behavior |
|-------|----------|
| Filename only: `"file.set"` | Searches in `mt4_bt_sets` from .env (default: `./sets`) |
| Full path: `"C:\path\to\file.set"` | Uses exact path provided |

### `--terminal`

| Input | Behavior |
|-------|----------|
| Terminal ID: `"mt4-01"` | Looks up in .env file (keys starting with `mt4-`) |
| Full path: `"C:\path\to\terminal.exe"` | Uses exact path provided |

---

## All Arguments

| Argument | Description | Default | Mode |
|----------|-------------|---------|------|
| `--terminal` | Terminal ID (mt4-01/02/03/04) or full path to terminal.exe | - | RUN, FULL |
| `--ini` | Path to existing INI file | - | RUN |
| `--output-ini` | Path to save generated INI | - | GEN |
| `--ea` | EA name with path (e.g., `KO\GM(Pro)_V1.32_AlgoX_REAL.ex4`) | - | GEN, FULL |
| `--set` | Set file name or full path | - | GEN, FULL |
| `--symbol` | Symbol (EURUSD, GBPNZD, etc.) | - | GEN, FULL |
| `--period` | Timeframe (M1, M5, H1, H4, D1, etc.) | H1 | GEN, FULL |
| `--model` | 0=Every tick, 1=Control points, 2=Open prices | 0 | GEN, FULL |
| `--spread` | Spread value | 0 | GEN, FULL |
| `--fromdate` | Start date YYYY.MM.DD | 1970.01.01 | GEN, FULL |
| `--todate` | End date YYYY.MM.DD | 1970.01.01 | GEN, FULL |
| `--report` | Report filename (include .htm) | auto-generated | GEN, FULL |
| `--replace-report` | Overwrite existing report (true/false) | true | GEN, FULL |
| `--shutdown` | Auto-close terminal (true/false) | true | GEN, FULL |
| `--profile` | Profile to load | - | GEN, FULL |
| `--optimization` | Enable optimization (true/false) | false | GEN, FULL |
| `--timeout` | Max seconds to wait | 3600 | RUN, FULL |
| `--tickdata-src` | TDS data source | Dukascopy | RUN, FULL |
| `--report-path` | Directory OR full file path for report | ./results | RUN, FULL |
| `--env` | Path to .env file | .env | All |

---

## Examples

### FULL Mode - Basic (uses defaults)
```bash
python scripts/mt4_runner.py \
  --terminal mt4-01 \
  --ea "KO\GM(Pro)_V1.32_AlgoX_REAL.ex4" \
  --set 7221_GBPNZD_B_M1_125_6k38_11.set \
  --symbol GBPNZD \
  --period M1 \
  --spread 10 \
  --fromdate "2026-01-01" \
  --todate "2026-02-01" \
  --model 0
```

### FULL Mode - Custom Report Name
```bash
python scripts/mt4_runner.py \
  --terminal mt4-01 \
  --ea "KO\GM(Pro)_V1.32_AlgoX_REAL.ex4" \
  --set 7221_GBPNZD_B_M1_125_6k38_11.set \
  --symbol GBPNZD \
  --period M1 \
  --spread 10 \
  --fromdate "2026-01-01" \
  --todate "2026-02-01" \
  --model 0 \
  --report-path "output/7221_S10.htm"
```

### Parallel Tests (4 terminals)
```bash
# Terminal 1 - Spread 1
python scripts/mt4_runner.py --terminal mt4-01 --ea "KO\GM(Pro)_V1.32_AlgoX_REAL.ex4" --set 7221_GBPNZD_B_M1_125_6k38_11.set --symbol GBPNZD --period M1 --spread 1 --fromdate "2026-01-01" --todate "2026-02-01" --model 0 --report-path "output/7221_S1.htm" --timeout 600 &

# Terminal 2 - Spread 10
python scripts/mt4_runner.py --terminal mt4-02 --ea "KO\GM(Pro)_V1.32_AlgoX_REAL.ex4" --set 7221_GBPNZD_B_M1_125_6k38_11.set --symbol GBPNZD --period M1 --spread 10 --fromdate "2026-01-01" --todate "2026-02-01" --model 0 --report-path "output/7221_S10.htm" --timeout 600 &

# Terminal 3 - Spread 20
python scripts/mt4_runner.py --terminal mt4-03 --ea "KO\GM(Pro)_V1.32_AlgoX_REAL.ex4" --set 7221_GBPNZD_B_M1_125_6k38_11.set --symbol GBPNZD --period M1 --spread 20 --fromdate "2026-01-01" --todate "2026-02-01" --model 0 --report-path "output/7221_S20.htm" --timeout 600 &

# Terminal 4 - Spread 30
python scripts/mt4_runner.py --terminal mt4-04 --ea "KO\GM(Pro)_V1.32_AlgoX_REAL.ex4" --set 7221_GBPNZD_B_M1_125_6k38_11.set --symbol GBPNZD --period M1 --spread 30 --fromdate "2026-01-01" --todate "2026-02-01" --model 0 --report-path "output/7221_S30.htm" --timeout 600 &
```

---

## Output Files

| File | Location |
|------|----------|
| Report (.htm) | Moved to `--report-path` directory |
| Chart (.gif) | Also copied with report |
| INI (.ini) | Saved in `mt4_bt_ini` directory |

---

## .env File Format

```ini
# Terminals (mt4-XX format)
mt4-01=C:\path\to\terminal.exe
mt4-02=C:\path\to\terminal.exe

# Optional directories (if not specified, uses code defaults)
mt4_bt_output=.\output
mt4_bt_ini=.\configs
mt4_bt_sets=.\sets
```

---

## TDS Data Sources

| Source | Usage |
|--------|-------|
| Dukascopy | Default - most pairs |
| Alpari-Standard1 | GBPSGD only |
