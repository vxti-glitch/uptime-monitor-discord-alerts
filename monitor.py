"""
uptime-monitor-discord-alerts
------------------------------
Pings a configurable list of hosts (IP addresses or domain names) on a
set interval and fires a Discord webhook alert when any host goes down or
comes back up.  All results are logged to a local CSV file.

Usage:
    1. Edit HOSTS and WEBHOOK_URL in config.py (or directly below).
    2. python monitor.py

Requirements:
    pip install requests
"""

import argparse
import csv
import datetime
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] requests is not installed. Run:  pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration — edit these
# ---------------------------------------------------------------------------

WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

DEFAULT_HOSTS = [
    {"name": "Google DNS",       "host": "8.8.8.8"},
    {"name": "Cloudflare DNS",   "host": "1.1.1.1"},
    {"name": "Google",           "host": "google.com"},
    # Add more hosts here:
    # {"name": "My Router",     "host": "192.168.1.1"},
]

CHECK_INTERVAL_SECONDS = 60     # how often to check (default: every 60 seconds)
PING_TIMEOUT_SECONDS   = 3      # seconds before a ping is considered failed
LOG_FILE               = "uptime_log.csv"


def load_hosts(config_path=None):
    """Load host definitions from JSON, or return built-in demo hosts."""
    if config_path is None:
        return list(DEFAULT_HOSTS)

    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    hosts = payload.get("hosts", payload) if isinstance(payload, dict) else payload
    if not isinstance(hosts, list):
        raise ValueError("Host config must be a list or an object with a 'hosts' list.")

    validated = []
    for idx, entry in enumerate(hosts, start=1):
        if not isinstance(entry, dict) or not entry.get("name") or not entry.get("host"):
            raise ValueError(f"Host entry {idx} must include 'name' and 'host'.")
        validated.append({"name": str(entry["name"]), "host": str(entry["host"])})
    return validated


# ---------------------------------------------------------------------------
# Ping function (cross-platform)
# ---------------------------------------------------------------------------

def ping(host, timeout=PING_TIMEOUT_SECONDS):
    """
    Returns True if host responds to ping, False otherwise.
    Uses the OS ping command so no extra libraries are needed.
    """
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout * 1000), host]
    else:
        cmd = ["ping", "-c", "1", "-W", str(timeout), host]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout + 2
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Discord alert
# ---------------------------------------------------------------------------

def send_discord_alert(message, webhook_url=None):
    """Send a plain-text message to the configured Discord webhook."""
    webhook_url = webhook_url or WEBHOOK_URL
    if not webhook_url:
        print("[WARNING] Discord webhook URL not set - skipping alert.")
        return

    payload = {"content": message}
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code not in (200, 204):
            print(f"[WARNING] Discord webhook returned {response.status_code}: {response.text}")
    except requests.RequestException as e:
        print(f"[WARNING] Failed to send Discord alert: {e}")


# ---------------------------------------------------------------------------
# CSV logger
# ---------------------------------------------------------------------------

def log_result(host_name, host_addr, status, note="", log_file=LOG_FILE):
    """Append a result row to the CSV log file."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_path.is_file()
    with log_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "Host Name", "Host Address", "Status", "Note"])
        writer.writerow([
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            host_name,
            host_addr,
            status,
            note,
        ])


# ---------------------------------------------------------------------------
# Monitor loop
# ---------------------------------------------------------------------------

def check_hosts(hosts, previous_state, webhook_url, log_file, ping_func=ping, alert_func=send_discord_alert):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] Checking {len(hosts)} host(s)...")

    for entry in hosts:
        name = entry["name"]
        host = entry["host"]
        is_up = ping_func(host)
        status = "UP" if is_up else "DOWN"
        prev = previous_state.get(host)

        if prev is None:
            note = "Initial check"
            if not is_up:
                msg = f"[DOWN] {name} ({host}) is unreachable.\nTime: {now_str}"
                alert_func(msg, webhook_url)
        elif prev is True and not is_up:
            note = "Host went DOWN"
            msg = f"[DOWN] {name} ({host}) just went unreachable.\nTime: {now_str}"
            print(f"  [ALERT] {msg}")
            alert_func(msg, webhook_url)
        elif prev is False and is_up:
            note = "Host came back UP"
            msg = f"[UP] {name} ({host}) is back online.\nTime: {now_str}"
            print(f"  [ALERT] {msg}")
            alert_func(msg, webhook_url)
        else:
            note = "No change"

        icon = "[UP]" if is_up else "[DOWN]"
        print(f"  {icon} {name:<22} {host:<18} {status}")
        log_result(name, host, status, note, log_file)
        previous_state[host] = is_up

    return previous_state


def build_parser():
    parser = argparse.ArgumentParser(
        description="Uptime monitor with Discord state-change alerts."
    )
    parser.add_argument("--config", type=Path, help="JSON host config file.")
    parser.add_argument("--once", action="store_true", help="Run one check cycle and exit.")
    parser.add_argument("--interval", type=int, default=CHECK_INTERVAL_SECONDS, help="Seconds between checks.")
    parser.add_argument("--timeout", type=int, default=PING_TIMEOUT_SECONDS, help="Ping timeout in seconds.")
    parser.add_argument("--log-file", type=Path, default=Path(LOG_FILE), help="CSV log file path.")
    parser.add_argument(
        "--webhook-url",
        default=WEBHOOK_URL,
        help="Discord webhook URL. Defaults to DISCORD_WEBHOOK_URL environment variable.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    hosts = load_hosts(args.config)

    print("=" * 60)
    print("  UPTIME MONITOR — Discord Alert Edition")
    print(f"  Monitoring {len(hosts)} host(s) every {args.interval}s")
    print(f"  Log file: {Path(args.log_file).resolve()}")
    print("=" * 60)
    if not args.once:
        print("  Press Ctrl+C to stop.\n")

    # Track previous state so we only alert on transitions (UP→DOWN, DOWN→UP)
    # None = unknown (first check), True = up, False = down
    previous_state = {entry["host"]: None for entry in hosts}

    while True:
        previous_state = check_hosts(
            hosts,
            previous_state,
            args.webhook_url,
            args.log_file,
            ping_func=lambda host: ping(host, timeout=args.timeout),
        )
        if args.once:
            print("\n[OK] One check cycle complete.")
            return

        print(f"  Next check in {args.interval}s...\n")
        try:
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n[OK] Monitor stopped by user.")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[OK] Monitor stopped by user.")
