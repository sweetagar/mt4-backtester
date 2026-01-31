#!/usr/bin/env python3
"""
MT4 Backtest Report Parser

Parse MT4 HTML report files and extract metrics to CSV.
Groups trades into cycles (BUY/SELL separated) for SL/MDD dates.

Usage:
    python scripts/parse_report.py output/report.htm
    python scripts/parse_report.py output/
"""

import re
import argparse
from datetime import datetime
from collections import defaultdict
from pathlib import Path

import pandas as pd
from lxml import etree


# CSV output columns
CSV_COLUMNS = [
    'magic#', 'set_filename', 'symbol', 'direction', 'start_date', 'end_date',
    'spread', 'day_num', 'net_profit', 'mdd', 'pm_ratio', 'yrly_%',
    'trade_num', 'mthly_trades', 'mdd_date', 'sl_date', 'max_lot', 'max_lvl', 'ea_lvl',
    'dist', 'tp0', 'tp1'
]


def parse_param(params_string, param_name):
    """Extract parameter value from EA params string"""
    match = re.search(rf'{param_name}=([\d.]+)', params_string)
    if match:
        val = match.group(1)
        return int(val) if '.' not in val else float(val)
    return None


def parse_header(html_file):
    """Parse HTML header section - return dict of extracted values"""
    data = {
        'magic': None, 'symbol': None, 'spread': None,
        'start_date_raw': None, 'end_date_raw': None,
        'initial_deposit': None, 'net_profit': None,
        'mdd': None, 'trade_num': None,
        'buy_max': None, 'sell_max': None,
        'dist': None, 'tp0': None, 'tp1': None
    }

    context = etree.iterparse(html_file, events=('end',), tag='tr', html=True)

    for event, elem in context:
        cells = [c.text.strip() if c.text else '' for c in elem.findall('.//td')]
        text = ' '.join(cells)

        # Symbol
        if 'Symbol' in text and not data['symbol']:
            for i, c in enumerate(cells):
                if 'Symbol' in c and i + 1 < len(cells):
                    data['symbol'] = cells[i + 1].split()[0]

        # Period (actual trade dates - OUTSIDE parens)
        elif 'Period' in text and not data['start_date_raw']:
            for c in cells:
                m = re.search(r'(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})\s*-\s*(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2})', c)
                if m:
                    data['start_date_raw'] = m.group(1)
                    data['end_date_raw'] = m.group(2)

        # Initial deposit & Spread
        elif 'Initial deposit' in text:
            for i, c in enumerate(cells):
                if 'Initial deposit' in c and i + 1 < len(cells):
                    try: data['initial_deposit'] = float(cells[i + 1])
                    except: pass
                elif 'Spread' in c and i + 1 < len(cells):
                    try: data['spread'] = int(cells[i + 1])
                    except: pass

        # Total net profit
        elif 'Total net profit' in text and data['net_profit'] is None:
            for i, c in enumerate(cells):
                if 'Total net profit' in c and i + 1 < len(cells):
                    try: data['net_profit'] = float(cells[i + 1])
                    except: pass

        # Maximal drawdown
        elif 'Maximal drawdown' in text and data['mdd'] is None:
            for i, c in enumerate(cells):
                if 'Maximal drawdown' in c and i + 1 < len(cells):
                    m = re.search(r'([\d.]+)', cells[i + 1])
                    if m:
                        try: data['mdd'] = float(m.group(1))
                        except: pass

        # Total trades
        elif 'Total trades' in text and data['trade_num'] is None:
            for i, c in enumerate(cells):
                if 'Total trades' in c and i + 1 < len(cells):
                    try: data['trade_num'] = int(cells[i + 1])
                    except: pass

        # Parameters
        elif 'Parameters' in text and data['magic'] is None:
            params = ' '.join(cells)
            data['magic'] = parse_param(params, 'MagicNumber')
            data['buy_max'] = parse_param(params, 'buy_max_open_orders')
            data['sell_max'] = parse_param(params, 'sell_max_open_orders')
            data['dist'] = parse_param(params, 'entry_distince_2')
            data['tp0'] = parse_param(params, 'trailing_stop_1_point_reach')
            data['tp1'] = parse_param(params, 'trailing_stop_other_point_reach1')

        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    return data


def parse_trades(html_file):
    """Parse trade table - return list of trade dicts"""
    trades = []
    context = etree.iterparse(html_file, events=('end',), tag='tr', html=True)
    header_found = False

    for event, elem in context:
        cells = [c.text.strip() if c.text else '' for c in elem.findall('.//td')]

        # Find header
        if not header_found:
            if elem.attrib.get('bgcolor') == '#C0C0C0':
                headers = [c.text.strip().lower() if c.text else '' for c in elem.findall('.//td')]
                if any('time' in h for h in headers) and len(headers) >= 8:
                    header_found = True
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
            continue

        # Parse trade row
        if header_found and len(cells) >= 8:
            try:
                trade = {
                    'trade_num': int(cells[0]),
                    'time': datetime.strptime(cells[1], '%Y.%m.%d %H:%M'),
                    'type': cells[2],
                    'order_id': int(cells[3]),
                    'size': float(cells[4]),
                    'profit': float(cells[8]) if cells[8] else None
                }
                trades.append(trade)
            except (ValueError, IndexError):
                pass

        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    return trades


def match_trades(trades):
    """Match open/close trades - return list of closed trades"""
    open_trades = {}
    closed = []

    for t in trades:
        if t['type'] in ['buy', 'sell']:
            open_trades[t['order_id']] = t
        elif t['type'] in ['close', 'close at stop']:
            oid = t['order_id']
            if oid in open_trades:
                closed.append({
                    'direction': open_trades[oid]['type'],
                    'open_trade_num': open_trades[oid]['trade_num'],
                    'close_trade_num': t['trade_num'],
                    'open_time': open_trades[oid]['time'],
                    'close_time': t['time'],
                    'size': t['size'],
                    'profit': t['profit'],
                    'close_at_stop': t['type'] == 'close at stop'
                })
                del open_trades[oid]

    return closed


def identify_cycles(trades):
    """Group trades into cycles using trade_num for chronological ordering"""
    if not trades:
        return []

    # Sort by open_trade_num (chronological order from MT4)
    sorted_trades = sorted(trades, key=lambda x: x['open_trade_num'])
    active = []
    completed = []

    for t in sorted_trades:
        assigned = False
        for cycle in active:
            # Trade belongs to cycle if it opens BEFORE cycle's last trade closes
            if t['open_trade_num'] < cycle['latest_close_trade_num']:
                cycle['trades'].append(t)
                # Update latest close if this trade closes later
                if t['close_trade_num'] > cycle['latest_close_trade_num']:
                    cycle['latest_close_trade_num'] = t['close_trade_num']
                    cycle['latest_close_time'] = t['close_time']
                # Mark cycle as having close at stop if any trade does
                if t.get('close_at_stop', False):
                    cycle['has_close_at_stop'] = True
                assigned = True
                break

        if not assigned:
            active.append({
                'trades': [t],
                'latest_close_trade_num': t['close_trade_num'],
                'latest_close_time': t['close_time'],
                'has_close_at_stop': t.get('close_at_stop', False)
            })

        # Check for completed cycles BEFORE processing next trade
        # Cycle is complete if it closes before new trade opens
        for cycle in active:
            if cycle['latest_close_trade_num'] < t['open_trade_num']:
                completed.append(cycle)
        # Remove completed cycles from active
        active = [c for c in active if c['latest_close_trade_num'] >= t['open_trade_num']]

    completed.extend(active)

    # Add cycle metrics
    for cycle in completed:
        cycle['profit'] = sum(t['profit'] for t in cycle['trades'] if t['profit'])
        cycle['lots'] = sum(t['size'] for t in cycle['trades'])

    return completed


def parse_report(html_file, set_filename=None):
    """Parse single HTML report - return CSV row dict"""
    set_filename = set_filename or Path(html_file).stem
    print(f"  Parsing: {Path(html_file).name}")

    # Parse header
    header = parse_header(html_file)

    # Parse trades
    trades = parse_trades(html_file)
    closed_trades = match_trades(trades)

    # Separate BUY/SELL cycles
    buy_cycles = identify_cycles([t for t in closed_trades if t['direction'] == 'buy'])
    sell_cycles = identify_cycles([t for t in closed_trades if t['direction'] == 'sell'])
    all_cycles = buy_cycles + sell_cycles

    # Calculate metrics
    start_dt = datetime.strptime(header['start_date_raw'], '%Y.%m.%d %H:%M')
    end_dt = datetime.strptime(header['end_date_raw'], '%Y.%m.%d %H:%M')
    day_num = (end_dt - start_dt).days

    # Direction
    if header['buy_max'] and header['sell_max']:
        direction = 'BS'
    elif header['buy_max']:
        direction = 'B'
    elif header['sell_max']:
        direction = 'S'
    else:
        direction = 'UNKNOWN'

    # Max lot
    max_lot = max([t['size'] for t in closed_trades]) if closed_trades else 0

    # Max level (actual max orders in any cycle)
    max_lvl = max([len(c['trades']) for c in all_cycles]) if all_cycles else 0

    # MDD dates (cycles with max accumulated lots) - use | separator for CSV
    max_lots = max([c['lots'] for c in all_cycles]) if all_cycles else 0
    mdd_dates = [c['latest_close_time'].strftime('%Y.%m.%d %H:%M') for c in all_cycles if c['lots'] == max_lots]

    # SL dates (loss cycles, excluding close at stop) - use | separator for CSV, include loss amount
    sl_dates = [f"{c['latest_close_time'].strftime('%Y.%m.%d %H:%M')} ({c['profit']:.2f})"
                for c in all_cycles if c['profit'] < 0 and not c.get('has_close_at_stop', False)]

    # EA level
    if direction == 'B':
        ea_lvl = header['buy_max']
    elif direction == 'S':
        ea_lvl = header['sell_max']
    else:
        ea_lvl = max(header['buy_max'] or 0, header['sell_max'] or 0)

    # Build row
    row = {
        'magic#': header['magic'],
        'set_filename': set_filename,
        'symbol': header['symbol'],
        'direction': direction,
        'start_date': start_dt.strftime('%Y.%m.%d %H:%M'),
        'end_date': end_dt.strftime('%Y.%m.%d %H:%M'),
        'spread': header['spread'],
        'day_num': day_num,
        'mdd': header['mdd'],
        'net_profit': header['net_profit'],
        'pm_ratio': round(header['net_profit'] / header['mdd'], 4) if header['mdd'] else 0,
        'yrly_%': round((header['net_profit'] / header['mdd'] / day_num) * 365, 4) if header['mdd'] and day_num else 0,
        'trade_num': header['trade_num'],
        'mthly_trades': round(header['trade_num'] / (day_num / 30), 2) if day_num else 0,
        'mdd_date': '|'.join(mdd_dates),
        'sl_date': '|'.join(sl_dates),
        'max_lot': max_lot,
        'max_lvl': max_lvl,
        'ea_lvl': ea_lvl,
        'dist': header['dist'],
        'tp0': header['tp0'],
        'tp1': header['tp1'],
    }

    print(f"    {direction} | {header['symbol']} | Profit: {header['net_profit']} | Trades: {header['trade_num']} | Cycles: {len(all_cycles)}")
    return row


def main():
    parser = argparse.ArgumentParser(description='Parse MT4 backtest HTML reports')
    parser.add_argument('input', help='HTML file or directory')
    parser.add_argument('-o', '--output', nargs='?', const='bt_output_log.csv',
                        help='Output CSV file (default: print to stdout only)')
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        exit(1)

    # Output to CSV if --output specified
    if args.output is not None:
        results = []
        if input_path.is_file():
            results.append(parse_report(input_path))
        else:
            htm_files = list(input_path.glob('*.htm'))
            print(f"Found {len(htm_files)} files")
            for f in htm_files:
                try:
                    results.append(parse_report(f))
                except Exception as e:
                    print(f"    ERROR: {e}")

        output_path = Path(args.output)
        df_new = pd.DataFrame(results)

        if output_path.exists():
            # Read existing CSV and append
            df_existing = pd.read_csv(output_path)
            df_existing.columns = df_existing.columns.str.strip()
            columns = df_existing.columns.tolist()
            df_new = df_new[columns]
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(output_path, index=False)
            print(f"\nAppended {len(results)} rows to {args.output} (total: {len(df_combined)})")
        else:
            df_new = df_new[CSV_COLUMNS]
            df_new.to_csv(output_path, index=False)
            print(f"\nExported {len(results)} rows to {args.output}")
    else:
        # Print to stdout only - print each file immediately
        if input_path.is_file():
            row = parse_report(input_path)
            print(",".join(CSV_COLUMNS))
            print(",".join(str(row[col]) for col in CSV_COLUMNS) + "\n")
        else:
            htm_files = list(input_path.glob('*.htm'))
            print(f"Found {len(htm_files)} files")
            for f in htm_files:
                try:
                    row = parse_report(f)
                    print(",".join(CSV_COLUMNS))
                    print(",".join(str(row[col]) for col in CSV_COLUMNS) + "\n")
                except Exception as e:
                    print(f"    ERROR: {e}")


if __name__ == "__main__":
    main()
