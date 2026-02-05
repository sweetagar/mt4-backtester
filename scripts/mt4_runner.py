#!/usr/bin/env python3
"""
MT4 Backtest Runner

Core script for running MT4 backtests from command line.
Supports three modes: gen_ini (generate INI only), run (run with existing INI),
and full (generate INI + run).

Usage:
    # Generate INI only
    python mt4_runner.py --ea "EA Name" --symbol EURUSD --output-ini config.ini

    # Run with existing INI
    python mt4_runner.py --terminal mt4-01 --ini config.ini

    # Generate INI + Run (one-shot)
    python mt4_runner.py --ea "EA Name" --symbol EURUSD --terminal mt4-01
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Version
__version__ = "1.0.0"

# Default directories
DEFAULT_ENV = ".env"
DEFAULT_TIMEOUT = 3600  # 1 hour

# Default backtest parameters
DEFAULT_MODEL = 0
DEFAULT_PERIOD = "H1"
DEFAULT_SPREAD = 0
DEFAULT_FROM_DATE = "1970.01.01"
DEFAULT_TO_DATE = "1970.01.01"
DEFAULT_REPLACE_REPORT = True
DEFAULT_SHUTDOWN = True
DEFAULT_TICKDATA_SRC = "Dukascopy"


def load_terminals(env_path: str = DEFAULT_ENV) -> dict:
    """Load terminal paths from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Dict mapping terminal IDs to paths
    """
    terminals = {}
    env_file = Path(env_path)

    if load_dotenv and env_file.exists():
        load_dotenv(env_file)
        # Use key directly as terminal ID (case-insensitive)
        # Format: mt4-01=path, primary=path, etc.
        for key, value in os.environ.items():
            key_lower = key.lower()
            # Accept mt4-*, primary, or other terminal IDs
            if key_lower.startswith("mt4-") or key_lower in ["primary", "mt4primary"]:
                term_id = key_lower.replace("mt4primary", "primary")
                terminals[term_id] = value

    if not terminals:
        raise ValueError(f"No terminals found in {env_path}. Use format: mt4-01=path")

    return terminals


def load_config(env_path: str = DEFAULT_ENV) -> dict:
    """Load output, ini, and sets paths from .env file.

    Args:
        env_path: Path to .env file

    Returns:
        Dict with 'output', 'ini', 'sets', and 'spread_params' paths/keys
    """
    config = {
        "output": "./output",
        "ini": "./configs",
        "sets": "./sets",
        "spread_params": []
    }
    env_file = Path(env_path)

    if load_dotenv and env_file.exists():
        load_dotenv(env_path)
        if "mt4_bt_output" in os.environ:
            config["output"] = os.environ["mt4_bt_output"]
        if "mt4_bt_ini" in os.environ:
            config["ini"] = os.environ["mt4_bt_ini"]
        if "mt4_bt_sets" in os.environ:
            config["sets"] = os.environ["mt4_bt_sets"]
        if "mt4_spread_params" in os.environ:
            # Parse comma-separated param names
            config["spread_params"] = [p.strip() for p in os.environ["mt4_spread_params"].split(",")]

    return config


def resolve_terminal(terminal_ref: str, env_path: str = DEFAULT_ENV) -> str:
    """Resolve terminal ID or path to full terminal.exe path.

    Args:
        terminal_ref: Terminal ID (mt4-01) or full path
        env_path: Path to .env file

    Returns:
        Full path to terminal.exe

    Raises:
        ValueError: If terminal not found
    """
    # Check if it's already a full path
    if "\\" in terminal_ref or "/" in terminal_ref:
        if Path(terminal_ref).exists():
            return terminal_ref
        raise ValueError(f"Terminal not found: {terminal_ref}")

    # Look up in registry
    terminals = load_terminals(env_path)
    terminal_ref = terminal_ref.lower()

    if terminal_ref not in terminals:
        available = ", ".join(terminals.keys())
        raise ValueError(f"Unknown terminal: {terminal_ref}. Available: {available}")

    path = terminals[terminal_ref]
    if not Path(path).exists():
        raise ValueError(f"Terminal not found: {path}")

    return path


def resolve_set_file(set_ref: str, sets_dir: str) -> tuple:
    """Resolve set file reference to full path and filename.

    Args:
        set_ref: Set file reference (filename or full path)
        sets_dir: Default sets directory from .env

    Returns:
        Tuple of (full_path, filename_only)

    Raises:
        FileNotFoundError: If set file not found
    """
    # Check if it's already a full path
    if "\\" in set_ref or "/" in set_ref:
        set_path = Path(set_ref)
        if set_path.exists():
            return str(set_path), set_path.name
        raise FileNotFoundError(f"Set file not found: {set_ref}")

    # Just a filename - use sets_dir from .env
    set_path = Path(sets_dir) / set_ref
    if set_path.exists():
        return str(set_path), set_ref

    raise FileNotFoundError(f"Set file not found: {set_path}")


def set_tickdata_source(terminal_path: str, source: str) -> bool:
    """Set TDS data source in tds.config if not already set.

    Args:
        terminal_path: Path to terminal.exe
        source: Data source name (e.g., Dukascopy, Alpari-Standard1)

    Returns:
        True if changed, False if already matching
    """
    tds_config = Path(terminal_path).parent / "config" / "tds.config"

    if not tds_config.exists():
        print(f"Warning: TDS config not found: {tds_config}")
        return False

    with open(tds_config) as f:
        content = f.read()

    # Check current value
    match = re.search(r'<add key="Source" value="([^"]+)" />', content)
    current = match.group(1) if match else None

    if current == source:
        return False  # Already set, no change

    # Replace only if different
    content = re.sub(
        r'<add key="Source" value="[^"]+" />',
        f'<add key="Source" value="{source}" />',
        content
    )

    with open(tds_config, 'w') as f:
        f.write(content)

    return True


def check_spread_params(set_file_path: str, test_spread: int, spread_params: list) -> dict:
    """Check if test spread exceeds EA params in set file.

    Args:
        set_file_path: Path to .set file
        test_spread: Spread value for backtest
        spread_params: List of param names to check (from .env)

    Returns:
        Dict of {param_name: (old_value, new_value)} for params needing adjustment
    """
    if not spread_params:
        return {}

    # Parse set file (skip optimization lines with commas)
    param_values = {}
    with open(set_file_path) as f:
        for line in f:
            line = line.strip()
            # Skip lines with commas (optimization params)
            if "," in line or not line:
                continue
            # Check for each spread param
            for param in spread_params:
                if line.startswith(f"{param}="):
                    try:
                        value = float(line.split("=")[1])
                        param_values[param] = value
                    except (ValueError, IndexError):
                        pass

    # Check if test spread exceeds or equals any param (with -1 allowance)
    adjustments = {}
    for param, value in param_values.items():
        if test_spread >= value - 1:
            adjustments[param] = (value, test_spread + 10)

    return adjustments


def adjust_copied_set_file(copied_set_path: str, adjustments: dict) -> None:
    """Modify the COPIED set file (in mt4/tester) with adjusted parameter values.

    Args:
        copied_set_path: Path to the COPIED .set file in mt4/tester folder
        adjustments: {param_name: (old_value, new_value)}
    """
    with open(copied_set_path) as f:
        lines = f.readlines()

    modified = []
    for line in lines:
        modified_line = line
        for param, (old_val, new_val) in adjustments.items():
            # Check for param=value line (skip optimization lines)
            if line.strip().startswith(f"{param}=") and "," not in line:
                # Preserve formatting: keep decimal places from original
                original_value_str = line.split("=")[1].strip()
                # Format new value with same decimal places
                if "." in original_value_str:
                    decimals = len(original_value_str.split(".")[1])
                    new_val_str = f"{new_val:.{decimals}f}"
                else:
                    new_val_str = str(int(new_val))
                modified_line = f"{param}={new_val_str}\n"
                break
        modified.append(modified_line)

    with open(copied_set_path, 'w') as f:
        f.writelines(modified)


def generate_report_name(set_file: str, spread: int = None, suffix: str = None) -> str:
    """Generate report name from set file + spread + timestamp.

    Args:
        set_file: Set file name (with or without .set extension)
        spread: Test spread value (optional)
        suffix: Optional suffix (e.g., "_extra")

    Returns:
        Report name: setfilename_S<spread>_YYYYMMDD_HHMMSS.htm
                    or setfilename_YYYYMMDD_HHMMSS.htm if no spread
    """
    base = Path(set_file).stem  # Remove .set extension
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if spread is not None:
        return f"{base}_S{spread}_{timestamp}.htm"
    return f"{base}_{timestamp}.htm"


def parse_report_path(report_path: str) -> tuple:
    """Parse report path into directory and filename.

    Args:
        report_path: Path to report (directory or full file path)

    Returns:
        Tuple of (directory, filename or None)
    """
    path = Path(report_path)

    # Check if it's a full file path (ends with .htm)
    if path.suffix.lower() == '.htm':
        return str(path.parent), path.name
    else:
        # It's just a directory
        return str(path), None


def build_ini_content(args: argparse.Namespace) -> str:
    """Build INI file content from arguments.

    Args:
        args: Parsed command line arguments

    Returns:
        INI file content as string
    """
    lines = [
        "; MT4 Backtest Configuration",
        f"; Generated by mt4_runner.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # Add profile if specified
    if hasattr(args, 'profile') and args.profile:
        lines.append(f"Profile={args.profile}")
        lines.append("")

    # Strategy Tester section
    lines.append(f"TestExpert={args.ea}")
    lines.append(f"TestExpertParameters={args.set}")

    if hasattr(args, 'symbol') and args.symbol:
        lines.append(f"TestSymbol={args.symbol}")

    if hasattr(args, 'period') and args.period:
        lines.append(f"TestPeriod={args.period}")

    if hasattr(args, 'model') and args.model is not None:
        lines.append(f"TestModel={args.model}")

    if hasattr(args, 'spread') and args.spread is not None:
        lines.append(f"TestSpread={args.spread}")

    if hasattr(args, 'optimization') and args.optimization:
        lines.append(f"TestOptimization={str(args.optimization).lower()}")

    # Date range
    if hasattr(args, 'fromdate') and args.fromdate:
        lines.append("TestDateEnable=true")
        lines.append(f"TestFromDate={args.fromdate}")
    if hasattr(args, 'todate') and args.todate:
        lines.append(f"TestToDate={args.todate}")

    # Report
    if hasattr(args, 'report') and args.report:
        # User specified report name via --report
        report = args.report
        if not report.endswith('.htm'):
            report += '.htm'
        lines.append(f"TestReport=tester\\{report}")
    elif hasattr(args, 'report_filename') and args.report_filename:
        # Filename extracted from --report-path (e.g., "myreport_S10.htm")
        lines.append(f"TestReport=tester\\{args.report_filename}")
    elif hasattr(args, 'set') and args.set:
        # GEN/FULL mode: generate report name from set file + spread + timestamp
        report_spread = args.spread if hasattr(args, 'spread') and args.spread else None
        report = generate_report_name(args.set, report_spread)
        lines.append(f"TestReport=tester\\{report}")

    if hasattr(args, 'replace_report') and args.replace_report is not None:
        lines.append(f"TestReplaceReport={str(args.replace_report).lower()}")

    if hasattr(args, 'shutdown') and args.shutdown is not None:
        lines.append(f"TestShutdownTerminal={str(args.shutdown).lower()}")

    return "\n".join(lines) + "\n"


def run_backtest(
    terminal_path: str,
    ini_path: str,
    timeout: int = DEFAULT_TIMEOUT,
    tickdata_src: Optional[str] = None,
    report_path: Optional[str] = None
) -> dict:
    """Run MT4 backtest.

    Args:
        terminal_path: Full path to terminal.exe
        ini_path: Path to INI configuration file
        timeout: Max seconds to wait for completion
        tickdata_src: TDS data source (default: Dukascopy)
        report_path: Directory to move reports after test (default: None = don't move)

    Returns:
        Dict with success, report_path, duration, error
    """
    import time

    # Set TDS source
    source = tickdata_src or DEFAULT_TICKDATA_SRC
    tds_changed = set_tickdata_source(terminal_path, source)
    if tds_changed:
        print(f"[TDS] Source set to: {source}")

    # Resolve paths
    terminal = Path(terminal_path)
    ini = Path(ini_path)

    if not terminal.exists():
        return {
            "success": False,
            "error": f"Terminal not found: {terminal}",
            "report_path": None,
            "duration": 0
        }

    if not ini.exists():
        return {
            "success": False,
            "error": f"INI file not found: {ini}",
            "report_path": None,
            "duration": 0
        }

    # Build command: terminal.exe /portable "path\to\config.ini"
    cmd = [str(terminal), "/portable", str(ini.absolute())]

    print(f"[MT4] Starting: {terminal.name}")
    print(f"[MT4] Config: {ini}")
    print(f"[MT4] Timeout: {timeout}s")

    start_time = time.time()

    try:
        # Run and wait for completion
        result = subprocess.run(
            cmd,
            timeout=timeout,
            capture_output=True,
            text=True
        )

        duration = time.time() - start_time

        if result.returncode != 0:
            return {
                "success": False,
                "error": f"MT4 exited with code {result.returncode}",
                "report_path": None,
                "duration": duration
            }

        # Find report path
        report_file = find_report(terminal, ini)

        if not report_file:
            return {
                "success": False,
                "error": f"Report not found after backtest. Expected location: {terminal.parent / 'tester'}",
                "report_path": None,
                "duration": duration
            }

        # Check for data availability issues
        import sys
        skill_dir = Path(__file__).parent
        sys.path.insert(0, str(skill_dir))
        try:
            from parse_report import parse_header
            report_data = parse_header(report_file)

            ZERO_DATE = "1970.01.01"
            start = report_data.get('start_date_raw', '')
            end = report_data.get('end_date_raw', '')
            trades = report_data.get('trade_num', 0)

            # Error 1: ZERO_DATA (TDS indexing)
            if start.startswith(ZERO_DATE) or end.startswith(ZERO_DATE):
                return {
                    "success": False,
                    "error": "ZERO_DATA: Data not available",
                    "report_path": str(report_file),
                    "duration": duration
                }

            # Error 2: Zero Time Range (start == end)
            if start and end and start.split()[0] == end.split()[0]:  # Compare date part only
                return {
                    "success": False,
                    "error": "ZERO_TIME_RANGE: Start date equals End date",
                    "report_path": str(report_file),
                    "duration": duration
                }

            # Warning 3: Zero trades - WARNING only, continue
            if trades == 0:
                print(f"[WARN] Zero trades in report - EA may not have taken any trades")
        except ImportError:
            # parse_report.py not available - skip check
            pass
        except Exception as e:
            # Parse error - continue, will be caught by full parse later
            pass

        # Move report to target directory if specified
        if report_path:
            try:
                report_file = move_report(report_file, report_path)
            except FileNotFoundError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "report_path": None,
                    "duration": duration
                }

        return {
            "success": True,
            "report_path": str(report_file),
            "duration": duration,
            "error": None
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Timeout after {timeout}s",
            "report_path": None,
            "duration": timeout
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "report_path": None,
            "duration": time.time() - start_time
        }


def move_report(source: Path, target_dir: str) -> Path:
    """Move report file and associated GIF to target directory.

    Args:
        source: Source report path (.htm)
        target_dir: Target directory path

    Returns:
        Final report path

    Raises:
        FileNotFoundError: If source report doesn't exist
    """
    import shutil

    if not source.exists():
        raise FileNotFoundError(f"Report not found: {source}")

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)
    final_path = target / source.name

    # Move .htm file
    shutil.move(str(source), str(final_path))

    # Also copy .gif file if it exists (MT4 generates chart images)
    gif_source = source.with_suffix('.gif')
    if gif_source.exists():
        gif_target = target / gif_source.name
        shutil.copy2(str(gif_source), str(gif_target))

    return final_path


def find_report(terminal_path: Path, ini_path: Path) -> Optional[Path]:
    """Find the generated report file.

    Args:
        terminal_path: Path to terminal.exe
        ini_path: Path to INI file used

    Returns:
        Path to report.htm, or None if not found
    """
    # Try to extract report name from INI
    with open(ini_path) as f:
        content = f.read()

    match = re.search(r'TestReport=([^\r\n]+)', content)
    if not match:
        return None

    report_name = match.group(1)

    # Report path is relative to terminal directory
    report_path = terminal_path.parent / report_name

    if not report_path.exists():
        return None

    return report_path


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MT4 Backtest Runner - Generate INI and run backtests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate INI only
  python mt4_runner.py --ea "KO\\GM(Pro)_V1.33_AlgoX_REAL" --set file.set --symbol EURUSD --output-ini config.ini

  # Run with existing INI
  python mt4_runner.py --terminal mt4-01 --ini config.ini

  # Generate INI + Run (one-shot)
  python mt4_runner.py --ea "KO\\GM(Pro)_V1.33_AlgoX_REAL" --set file.set --symbol EURUSD --terminal mt4-01
        """
    )

    # Mode selection (mutually exclusive, but handled via logic)
    parser.add_argument("--terminal", help="Terminal ID (mt4-01/02/03) or full path")
    parser.add_argument("--ini", help="Path to existing INI file (run mode)")
    parser.add_argument("--output-ini", help="Path to save generated INI (gen mode)")

    # Environment
    parser.add_argument("--env", default=DEFAULT_ENV, help=f"Path to .env file (default: {DEFAULT_ENV})")

    # Backtest parameters (for gen/full mode)
    parser.add_argument("--ea", help="EA name (e.g., KO\\GM(Pro)_V1.33_AlgoX_REAL)")
    parser.add_argument("--set", help="Set file name (in \\tester folder)")
    parser.add_argument("--symbol", help="Symbol (e.g., EURUSD)")
    parser.add_argument("--period", default=DEFAULT_PERIOD, help="Timeframe (default: H1)")
    parser.add_argument("--model", type=int, default=DEFAULT_MODEL, choices=[0, 1, 2],
                        help="Test model: 0=Every tick, 1=Control points, 2=Open prices (default: 0)")
    parser.add_argument("--spread", type=int, default=DEFAULT_SPREAD, help=f"Spread value (default: {DEFAULT_SPREAD})")
    parser.add_argument("--fromdate", default=DEFAULT_FROM_DATE, help=f"Start date YYYY.MM.DD (default: {DEFAULT_FROM_DATE})")
    parser.add_argument("--todate", default=DEFAULT_TO_DATE, help=f"End date YYYY.MM.DD (default: {DEFAULT_TO_DATE})")
    parser.add_argument("--report", help="Report filename (include .htm)")
    parser.add_argument("--replace-report", type=lambda x: x.lower() == 'true',
                        default=DEFAULT_REPLACE_REPORT, help="Overwrite existing report (default: true)")
    parser.add_argument("--shutdown", type=lambda x: x.lower() == 'true',
                        default=DEFAULT_SHUTDOWN, help="Auto-close terminal (default: true)")
    parser.add_argument("--profile", help="Profile to load (e.g., Default)")
    parser.add_argument("--optimization", type=lambda x: x.lower() == 'true',
                        default=False, help="Enable optimization (default: false)")

    # Execution parameters
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Max seconds to wait (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--tickdata-src", default=DEFAULT_TICKDATA_SRC,
                        help=f"TDS data source (default: {DEFAULT_TICKDATA_SRC})")
    parser.add_argument("--report-path", default="./results",
                        help="Directory to move reports after backtest (default: ./results)")

    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_args()

    # Load config from .env (output, ini directories)
    config = load_config(args.env)

    # Use default output from .env if --report-path not explicitly changed
    if args.report_path == "./results":
        args.report_path = config["output"]

    # Parse --report-path: extract directory and filename (if specified)
    report_dir, report_filename = parse_report_path(args.report_path)
    args.report_path = report_dir  # Update to directory only for run_backtest
    if report_filename:
        args.report_filename = report_filename

    # Determine mode
    has_ini = args.ini is not None
    has_output_ini = args.output_ini is not None
    has_terminal = args.terminal is not None
    has_ea_params = args.ea is not None

    # Mode detection
    if has_ini and has_terminal:
        # RUN mode: use existing INI
        mode = "run"
    elif has_output_ini and not has_terminal:
        # GEN mode: generate INI only
        mode = "gen"
    elif has_terminal and has_ea_params:
        # FULL mode: generate INI + run
        mode = "full"
    else:
        print("Error: Invalid argument combination.")
        print("\nValid modes:")
        print("  GEN:   --ea ... --output-ini config.ini")
        print("  RUN:   --terminal mt4-01 --ini config.ini")
        print("  FULL:  --ea ... --terminal mt4-01")
        sys.exit(1)

    # Process mode
    if mode == "gen":
        # Generate INI only
        ini_content = build_ini_content(args)
        output_path = Path(args.output_ini)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(ini_content)
        print(f"[INI] Generated: {output_path}")
        return 0

    elif mode == "run":
        # Run with existing INI
        terminal = resolve_terminal(args.terminal, args.env)
        result = run_backtest(
            terminal_path=terminal,
            ini_path=args.ini,
            timeout=args.timeout,
            tickdata_src=args.tickdata_src,
            report_path=args.report_path
        )

        if result["success"]:
            print(f"[DONE] Duration: {result['duration']:.1f}s")
            if result["report_path"]:
                print(f"[DONE] Report: {result['report_path']}")
            return 0
        else:
            print(f"[ERROR] {result['error']}")
            return 1

    elif mode == "full":
        # Resolve and copy set file to terminal's tester folder
        import shutil
        terminal = resolve_terminal(args.terminal, args.env)
        terminal_dir = Path(terminal).parent
        tester_dir = terminal_dir / "tester"

        set_full_path, set_filename = resolve_set_file(args.set, config["sets"])
        set_dest = tester_dir / set_filename

        # Copy set file to tester folder (always copy if source is newer or different)
        copy_needed = True
        if set_dest.exists():
            # Check if source is newer than destination
            src_mtime = Path(set_full_path).stat().st_mtime
            dst_mtime = set_dest.stat().st_mtime
            if src_mtime <= dst_mtime:
                copy_needed = False

        if copy_needed:
            shutil.copy2(set_full_path, set_dest)
            print(f"[SET] Copied: {set_filename} -> tester/")
        else:
            print(f"[SET] Skipped (up-to-date): {set_filename}")

        # Clear tester/files/ cache to avoid issues from previous runs
        files_dir = tester_dir / "files"
        if files_dir.exists():
            try:
                # Remove all .hcc, .hca, and other cache files
                for cache_file in files_dir.glob("*"):
                    cache_file.unlink()
                print(f"[SET] Cleared cache: tester/files/")
            except Exception as e:
                print(f"[WARN] Could not clear cache: {e}")

        # Check if test spread exceeds EA spread params (adjust copied file if needed)
        if hasattr(args, 'spread') and args.spread and config["spread_params"]:
            adjustments = check_spread_params(set_full_path, args.spread, config["spread_params"])
            if adjustments:
                print(f"[WARN] Test spread ({args.spread}) exceeds EA limits:")
                for param, (old_val, new_val) in adjustments.items():
                    print(f"       {param}: {old_val} -> {new_val}")
                # Modify the COPIED file in tester folder, not the original
                adjust_copied_set_file(str(set_dest), adjustments)
                print(f"[SET] Adjusted copied set file: {set_dest}")

        # Update args.set to just filename for INI generation
        args.set = set_filename

        # Generate INI to ini directory
        ini_dir = Path(config["ini"])
        ini_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename: setfile_S<spread>_timestamp.ini
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        set_name = Path(set_filename).stem
        test_spread = args.spread if hasattr(args, 'spread') and args.spread else 0
        if test_spread > 0:
            ini_filename = f"{set_name}_S{test_spread}_{timestamp}.ini"
        else:
            ini_filename = f"{set_name}_{timestamp}.ini"
        ini_path = ini_dir / ini_filename

        with open(ini_path, 'w') as f:
            f.write(build_ini_content(args))

        print(f"[INI] Generated: {ini_path}")

        result = run_backtest(
            terminal_path=terminal,
            ini_path=ini_path,
            timeout=args.timeout,
            tickdata_src=args.tickdata_src,
            report_path=args.report_path
        )

        if result["success"]:
            print(f"[DONE] Duration: {result['duration']:.1f}s")
            if result["report_path"]:
                print(f"[DONE] Report: {result['report_path']}")
            return 0
        else:
            print(f"[ERROR] {result['error']}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
