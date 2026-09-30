import re
import openpyxl
from datetime import datetime
from pathlib import Path

from logger_config import setup_logger
setup_logger()

import logging
logger = logging.getLogger(__name__)

THREADS_LOG = Path('logs/threads.log')
APP_LOG = Path('logs/logs.log')
OUTPUT_XLSX = Path('correlated_logs.xlsx')

def parse_logs(log_file):
    logs = []
    with open(log_file, encoding='utf-8') as f:
        for line in f:
            timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
            if timestamp_match:
                ts_str = timestamp_match.group(1)
                try:
                    ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S,%f")
                except ValueError:
                    continue
                logs.append((ts, line.strip()))
    return logs

def extract_thread_lifespans(thread_logs):
    thread_map = {}
    events = []  # New: list of entries: {ts, name, id, status, log_message}

    start_pattern = re.compile(r'\[THREAD STARTED\] *→ *(.+?) \(ID=(\d+)\)')
    end_pattern = re.compile(r'\[THREAD ENDED\] *→ *(.+?) \(ID=(\d+)\) ran for ([\d.]+) seconds')

    for ts, log in thread_logs:
        if "[THREAD STARTED]" in log:
            match = start_pattern.search(log)
            if match:
                name, tid = match.groups()
                thread_map[name] = {"start": ts, "end": None, "id": tid}
                events.append({
                    "time": ts,
                    "thread": name,
                    "tid": tid,
                    "status": "STARTED",
                    "msg": "---"
                })
        elif "[THREAD ENDED]" in log:
            match = end_pattern.search(log)
            if match:
                name, tid, duration = match.groups()
                if name in thread_map:
                    thread_map[name]["end"] = ts
                    events.append({
                        "time": ts,
                        "thread": name,
                        "tid": tid,
                        "status": "ENDED",
                        "msg": "---"
                    })
    return thread_map, events

def correlate_logs(app_logs, thread_map):
    results = []
    for ts, line in app_logs:
        matched = False
        for thread_name, tinfo in thread_map.items():
            if tinfo["start"] <= ts and (tinfo["end"] is None or ts <= tinfo["end"]):
                results.append({
                    "time": ts,
                    "thread": thread_name,
                    "tid": tinfo["id"],
                    "status": "ACTIVE",
                    "msg": line
                })
                matched = True
                break
        if not matched:
            results.append({
                "time": ts,
                "thread": "N/A",
                "tid": "N/A",
                "status": "UNKNOWN",
                "msg": line
            })
    return results

def save_to_excel(records, output_file):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Correlated Logs"

    # Headers
    ws.append(["Timestamp", "Thread Name", "Thread ID", "Thread Status", "App Log Message"])

    # Data
    for item in records:
        ws.append([
            item['time'].strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            item['thread'],
            item['tid'],
            item['status'],
            item['msg']
        ])

    # Auto-adjust column width
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(20, max_length + 2)

    wb.save(output_file)
    logger.info(f"Logs exported to Excel: {output_file.absolute()}")

def main():
    logger.info("Parsing logs...")
    thread_logs = parse_logs(THREADS_LOG)
    app_logs = parse_logs(APP_LOG)

    logger.info("Extracting thread lifespans...")
    thread_lifespans, thread_events = extract_thread_lifespans(thread_logs)

    logger.info("Correlating app log entries with threads...")
    correlated_app_logs = correlate_logs(app_logs, thread_lifespans)

    # Merge both into one list → maintain chronological order
    all_logs = thread_events + correlated_app_logs
    all_logs.sort(key=lambda x: x['time'])

    logger.info("Saving Excel report...")
    save_to_excel(all_logs, OUTPUT_XLSX)

if __name__ == '__main__':
    main()
