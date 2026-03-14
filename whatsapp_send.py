import glob
import json
import os
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

WAHA_URL = os.getenv("WAHA_URL", "http://localhost:3000")
WAHA_API_KEY = os.getenv("WAHA_API_KEY", "mysecret")
SESSION = os.getenv("WAHA_SESSION", "default")
MY_PHONE = os.getenv("MY_PHONE", "").strip()

SOURCE_ICON = {"classroom": "🔵", "moodle": "🟢", "cet": "🟡"}
SOURCE_NAME = {"classroom": "Classroom", "moodle": "Moodle", "cet": "CET"}

URGENCY_GROUPS = [
    ("🔴 *באיחור / היום*", lambda d: d is not None and d <= 0),
    ("🟠 *דחוף - עד יומיים*", lambda d: d is not None and 1 <= d <= 2),
    ("🟡 *השבוע - עד 7 ימים*", lambda d: d is not None and 3 <= d <= 7),
    ("🟢 *יש זמן*", lambda d: d is None or d > 7),
]


def send_whatsapp(text: str) -> bool:
    url = f"{WAHA_URL}/api/sendText"
    headers = {"Content-Type": "application/json", "X-Api-Key": WAHA_API_KEY}
    payload = {
        "session": SESSION,
        "chatId": f"{MY_PHONE}@s.whatsapp.net",
        "text": text,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
    except requests.RequestException as exc:
        print(f"Failed to contact WAHA: {exc}")
        return False

    if response.status_code in (200, 201):
        print("Message sent")
        return True

    print(f"Failed: {response.status_code} {response.text}")
    return False


def load_latest_tasks():
    files = glob.glob(os.path.join("all_tasks", "all_tasks_*.json"))
    if not files:
        print("No tasks found. Run run_all.py first.")
        return []

    latest = max(files, key=os.path.getmtime)
    print(f"Loading: {latest}")

    try:
        with open(latest, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read tasks file: {exc}")
        return []


def format_message(tasks) -> str:
    if not tasks:
        return "✅ אין משימות פתוחות כרגע!"

    def sort_key(task):
        days = task.get("days_left")
        return days if days is not None else 999

    tasks_sorted = sorted(tasks, key=sort_key)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    lines = [
        f"📚 *משימות פתוחות - {now}*",
        f"סה\"כ: {len(tasks)} משימות",
        "",
    ]

    for header, condition in URGENCY_GROUPS:
        group = [task for task in tasks_sorted if condition(task.get("days_left"))]
        if not group:
            continue

        lines.append(f"{header} ({len(group)})")
        for task in group:
            src = task.get("source", "")
            icon = SOURCE_ICON.get(src, "⚪")
            name = SOURCE_NAME.get(src, src)
            title = task.get("title", "")[:60]
            due = task.get("due_date")
            days = task.get("days_left")
            desc = task.get("description", "")[:80]

            lines.append(f"  {icon} *{title}* [{name}]")
            if due:
                if days is None:
                    days_txt = ""
                elif days < 0:
                    days_txt = f" (באיחור {abs(days)} ימים!)"
                elif days == 0:
                    days_txt = " (היום!)"
                else:
                    days_txt = f" ({days} ימים)"
                lines.append(f"    📅 {due}{days_txt}")

            if desc:
                lines.append(f"    📝 {desc}")

        lines.append("")

    return "\n".join(lines)


def main() -> None:
    if not MY_PHONE:
        print("Missing MY_PHONE in .env")
        return

    tasks = load_latest_tasks()
    message = format_message(tasks)

    print("\nMessage preview:")
    print(message)
    print()

    send_whatsapp(message)


if __name__ == "__main__":
    main()
