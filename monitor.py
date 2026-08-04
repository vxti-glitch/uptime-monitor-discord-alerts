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

import csv
import datetime
import os
import platform
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    print("[ERROR] requests is not installed. Run:  pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration — edit these
# ---------------------------------------------------------------------------

WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL_HERE"   # paste your Discord webhook URL

HOSTS = [
    {"name": "Google DNS",       "host": "8.8.8.8"},
    {"name": "Cloudflare DNS",   "host": "1.1.1.1"},
    {"name": "Google",           "host": "google.com"},
    # Add more hosts here:
    # {"name": "My Router",     "host": "192.168.1.1"},
]

CHECK_INTERVAL_SECONDS = 60     # how often to check (default: every 60 seconds)
PING_TIMEOUT_SECONDS   = 3      # seconds before a ping is considered failed
LOG_FILE               = "uptime_log.csv"


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

def send_discord_alert(message):
    """Send a plain-text message to the configured Discord webhook."""
    if WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        print("[WARNING] Discord webhook URL not set — skipping alert.")
        return

    payload = {"content": message}
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code not in (200, 204):
            print(f"[WARNING] Discord webhook returned {response.status_code}: {response.text}")
    except requests.RequestException as e:
        print(f"[WARNING] Failed to send Discord alert: {e}")


# ---------------------------------------------------------------------------
# CSV logger
# ---------------------------------------------------------------------------

def log_result(host_name, host_addr, status, note=""):
    """Append a result row to the CSV log file."""
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
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

def main():
    print("=" * 60)
    print("  UPTIME MONITOR — Discord Alert Edition")
    print(f"  Monitoring {len(HOSTS)} host(s) every {CHECK_INTERVAL_SECONDS}s")
    print(f"  Log file: {os.path.abspath(LOG_FILE)}")
    print("=" * 60)
    print("  Press Ctrl+C to stop.\n")

    # Track previous state so we only alert on transitions (UP→DOWN, DOWN→UP)
    # None = unknown (first check), True = up, False = down
    previous_state = {entry["host"]: None for entry in HOSTS}

    while True:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now_str}] Checking {len(HOSTS)} host(s)...")

        for entry in HOSTS:
            name = entry["name"]
            host = entry["host"]
            is_up = ping(host)
            status = "UP" if is_up else "DOWN"
            prev   = previous_state[host]

            # Determine if this is a state change
            if prev is None:
                # First check — establish baseline, alert if already down
                note = "Initial check"
                if not is_up:
                    msg = (
                        f"🔴 **DOWN** | {name} (`{host}`) is unreachable.\n"
                        f"Time: {now_str}"
                    )
                    send_discord_alert(msg)
            elif prev is True and not is_up:
                # Transition: UP → DOWN
                note = "Host went DOWN"
                msg = (
                    f"🔴 **DOWN** | {name} (`{host}`) just went unreachable.\n"
                    f"Time: {now_str}"
                )
                print(f"  [ALERT] {msg}")
                send_discord_alert(msg)
            elif prev is False and is_up:
                # Transition: DOWN → UP
                note = "Host came back UP"
                msg = (
                    f"🟢 **UP** | {name} (`{host}`) is back online.\n"
                    f"Time: {now_str}"
                )
                print(f"  [ALERT] {msg}")
                send_discord_alert(msg)
            else:
                note = "No change"

            icon = "✅" if is_up else "❌"
            print(f"  {icon} {name:<22} {host:<18} {status}")
            log_result(name, host, status, note)
            previous_state[host] = is_up

        print(f"  Next check in {CHECK_INTERVAL_SECONDS}s...\n")
        try:
            time.sleep(CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[✓] Monitor stopped by user.")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[✓] Monitor stopped by user.")
