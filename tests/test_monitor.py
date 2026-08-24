import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import monitor


class MonitorTests(unittest.TestCase):
    def test_load_hosts_from_config(self):
        with TemporaryDirectory() as tmp:
            config = Path(tmp) / "hosts.json"
            config.write_text(
                json.dumps({"hosts": [{"name": "Router", "host": "192.0.2.1"}]}),
                encoding="utf-8",
            )

            hosts = monitor.load_hosts(config)

        self.assertEqual(hosts, [{"name": "Router", "host": "192.0.2.1"}])

    def test_check_hosts_alerts_on_state_change_and_logs(self):
        with TemporaryDirectory() as tmp:
            log_file = Path(tmp) / "uptime.csv"
            alerts = []
            hosts = [{"name": "Router", "host": "192.0.2.1"}]
            state = {"192.0.2.1": True}

            monitor.check_hosts(
                hosts,
                state,
                "",
                log_file,
                ping_func=lambda host: False,
                alert_func=lambda message, webhook_url=None: alerts.append(message),
            )

            self.assertEqual(len(alerts), 1)
            self.assertIn("[DOWN]", alerts[0])
            with log_file.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["Status"], "DOWN")
            self.assertEqual(rows[0]["Note"], "Host went DOWN")


if __name__ == "__main__":
    unittest.main()
