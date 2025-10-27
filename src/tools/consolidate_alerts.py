import json
import os
from collections import defaultdict
from datetime import datetime

def consolidate_alerts():
    reports_dir = "/Users/tech/dev/development/stock_trading/reports"
    consolidated_dir = os.path.join(reports_dir, "consolidated", "deployment")
    os.makedirs(consolidated_dir, exist_ok=True)

    alert_files = []
    for root, dirs, files in os.walk(reports_dir):
        if "deployment" in root and "consolidated" not in root:
            for file in files:
                if file.startswith("alert_notification_") and file.endswith(".json"):
                    alert_files.append(os.path.join(root, file))

    alerts_by_day = defaultdict(list)

    for file_path in alert_files:
        try:
            with open(file_path, 'r') as f:
                alerts = json.load(f)
                if isinstance(alerts, list):
                    file_name = os.path.basename(file_path)
                    date_str = file_name.replace("alert_notification_", "").replace(".json", "")
                    alerts_by_day[date_str].extend(alerts)
        except (json.JSONDecodeError, FileNotFoundError):
            continue

    for day, alerts in alerts_by_day.items():
        alerts.sort(key=lambda x: datetime.strptime(x['alert_time'], '%Y-%m-%dT%H:%M:%S%z'))
        
        output_path = os.path.join(consolidated_dir, f"alert_notification_{day}.json")
        with open(output_path, 'w') as f:
            json.dump(alerts, f, indent=4)
        print(f"Consolidated {len(alerts)} alerts for {day} into {output_path}")

if __name__ == "__main__":
    consolidate_alerts()
