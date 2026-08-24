# Uptime Monitor with Discord Alerts

[github.com/vxti-glitch](https://github.com/vxti-glitch)

Pings a configurable list of hosts on a set interval and fires a Discord webhook alert the moment any host goes **down** or comes back **up**. All results are logged to a local CSV file for uptime records.

Built as an extension of my [webhook integration case study](https://github.com/vxti-glitch/case-study-webhook-integration).

---

## Example output

**Console:**
```
============================================================
  UPTIME MONITOR - Discord Alert Edition
  Monitoring 3 host(s) every 60s
  Log file: C:\tools\uptime_log.csv
============================================================
  Press Ctrl+C to stop.

[2026-08-03 20:15:00] Checking 3 host(s)...
  [UP] Google DNS            8.8.8.8            UP
  [UP] Cloudflare DNS        1.1.1.1            UP
  [UP] Google                google.com         UP
  Next check in 60s...

[2026-08-03 20:16:00] Checking 3 host(s)...
  [UP] Google DNS            8.8.8.8            UP
  [ALERT] [DOWN] Cloudflare DNS (1.1.1.1) just went unreachable.
  [DOWN] Cloudflare DNS        1.1.1.1            DOWN
  [UP] Google                google.com         UP
  Next check in 60s...
```

**Discord alert:**
```
[DOWN] Cloudflare DNS (1.1.1.1) just went unreachable.
Time: 2026-08-03 20:16:00
```

---

## Setup

```bash
# 1. Install dependency
pip install -r requirements.txt

# 2. Set the webhook outside source code
$env:DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/..."

# 3. Run continuously with the built-in demo hosts
python monitor.py

# Or run one check with a JSON host file
python monitor.py --config hosts.example.json --once --log-file logs/uptime.csv
```

**To get a Discord webhook URL:**
Server Settings -> Integrations -> Webhooks -> New Webhook -> Copy URL

---

## Features

- **Alert only on state changes** - no spam. You get one alert when a host goes down, one when it comes back up.
- **CSV logging** - every check is written to `uptime_log.csv` with timestamp, host, and status.
- **Config file support** - load host lists from JSON instead of editing source.
- **One-shot mode** - `--once` works well with Task Scheduler, cron, and tests.
- **Cross-platform ping** - works on Windows and Linux/Mac.
- **Zero infrastructure** - runs from any machine with Python installed, no server required.

Run tests:

```bash
python -m unittest discover -s tests -v
```

---

## Help Desk / NOC relevance

Automated uptime monitoring and alert routing are standard in NOC and Help Desk environments. Tools like PagerDuty, Nagios, and Zabbix do this at scale; this project demonstrates the same underlying logic (ping -> state-change detection -> webhook alert) implemented from scratch.

**Skills:** Python · Network connectivity testing · Discord webhook API · Event-driven alerting · CSV logging

---

*Part of the [vxti-glitch IT Support Portfolio](https://github.com/vxti-glitch)*
