import json
import os
import socket
import time
import traceback
from datetime import UTC, datetime

from dotenv import load_dotenv

from run_all import filter_relevant_tasks, main as run_all
from supabase_sync import is_supabase_configured, postgrest_request, sync_tasks_to_supabase

load_dotenv()

OUT_DIR = os.path.join(os.getcwd(), "all_tasks")
POLL_INTERVAL_SEC = max(5, int(os.getenv("AGENT_POLL_INTERVAL_SEC", "60")))
AGENT_NAME = os.getenv("AGENT_NAME", socket.gethostname())

os.makedirs(OUT_DIR, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def fetch_agent_settings():
    rows = postgrest_request(
        "GET",
        "agent_settings",
        params={"id": "eq.1", "limit": "1"},
    )
    return (rows or [None])[0]


def fetch_next_pending_command():
    rows = postgrest_request(
        "GET",
        "agent_commands",
        params={
            "status": "eq.pending",
            "order": "created_at.asc",
            "limit": "1",
        },
    )
    return (rows or [None])[0]


def update_last_auto_run():
    postgrest_request(
        "PATCH",
        "agent_settings",
        params={"id": "eq.1", "limit": "1"},
        json_body={"last_auto_run": utc_now_iso()},
        prefer="return=minimal",
    )


def claim_command(command_id: int):
    rows = postgrest_request(
        "PATCH",
        "agent_commands",
        params={
            "id": f"eq.{command_id}",
            "status": "eq.pending",
            "limit": "1",
        },
        json_body={
            "status": "running",
            "agent_name": AGENT_NAME,
            "started_at": utc_now_iso(),
            "result": None,
        },
        prefer="return=representation",
    )
    return (rows or [None])[0]


def finish_command(command_id: int, status: str, result: str):
    postgrest_request(
        "PATCH",
        "agent_commands",
        params={
            "id": f"eq.{command_id}",
            "limit": "1",
        },
        json_body={
            "status": status,
            "finished_at": utc_now_iso(),
            "result": result,
        },
        prefer="return=minimal",
    )


def run_single_scraper(command_name: str):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if command_name == "run_moodle":
        from moodle_extract_tasks import main as scraper_main

        source = "moodle"
    elif command_name == "run_cet":
        from cet_extract_tasks import main as scraper_main

        source = "cet"
    elif command_name == "run_classroom":
        from classroom_todo import main as scraper_main

        source = "classroom"
    else:
        raise ValueError(f"Unsupported command: {command_name}")

    tasks = scraper_main() or []
    for task in tasks:
        task.setdefault("source", source)

    filtered_tasks, removed_counts = filter_relevant_tasks(tasks)
    combined_path = os.path.join(OUT_DIR, f"all_tasks_{source}_{ts}.json")
    with open(combined_path, "w", encoding="utf-8") as handle:
        json.dump(filtered_tasks, handle, ensure_ascii=False, indent=2)

    sync_result = sync_tasks_to_supabase(
        filtered_tasks,
        run_key=f"{source}_{ts}",
        scraper_results={source: 0},
        combined_path=combined_path,
        deactivate_missing=False,
    )
    if sync_result["status"] != "success":
        raise RuntimeError(f"Supabase sync failed: {sync_result}")

    removed_summary = ", ".join(f"{key}={value}" for key, value in sorted(removed_counts.items())) or "none"
    return {
        "command": command_name,
        "source": source,
        "tasks": len(filtered_tasks),
        "filtered": removed_summary,
        "combined_path": combined_path,
        "sync": sync_result["uploaded_tasks"],
    }


def process_command(command_row: dict):
    command_name = str(command_row.get("command", "")).strip().lower()

    if command_name == "run_all":
        run_all()
        return {
            "command": command_name,
            "message": "run_all completed",
        }

    if command_name in {"run_moodle", "run_cet", "run_classroom"}:
        return run_single_scraper(command_name)

    raise ValueError(f"Unsupported command: {command_name}")


def daemon_loop():
    if not is_supabase_configured():
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    print(f"[Agent] Listening for commands as {AGENT_NAME} every {POLL_INTERVAL_SEC}s")

    while True:
        try:
            settings = None
            try:
                settings = fetch_agent_settings()
            except Exception as exc:
                print(f"[Agent] Settings fetch skipped: {exc}")

            if settings and settings.get("auto_run_enabled"):
                interval = int(settings.get("auto_run_interval_minutes", 30))
                last_run = settings.get("last_auto_run")

                if last_run:
                    last_run_time = datetime.fromisoformat(str(last_run).replace("Z", "+00:00"))
                    minutes_since = (datetime.now(UTC) - last_run_time).total_seconds() / 60
                else:
                    minutes_since = interval + 1

                if minutes_since >= interval:
                    print("[Agent] Running automatic run_all")
                    run_all()
                    update_last_auto_run()

            pending = fetch_next_pending_command()
            if not pending:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            claimed = claim_command(pending["id"])
            if not claimed:
                time.sleep(1)
                continue

            print(f"[Agent] Processing command #{claimed['id']}: {claimed['command']}")

            try:
                result = process_command(claimed)
                finish_command(claimed["id"], "done", json.dumps(result, ensure_ascii=False))
                print(f"[Agent] Command #{claimed['id']} completed")
            except Exception as exc:
                message = f"{type(exc).__name__}: {exc}"
                details = traceback.format_exc(limit=8)
                finish_command(claimed["id"], "error", f"{message}\n\n{details}"[:8000])
                print(f"[Agent] Command #{claimed['id']} failed: {message}")
        except KeyboardInterrupt:
            print("[Agent] Stopped")
            raise
        except Exception as exc:
            print(f"[Agent] Loop error: {exc}")
            time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    daemon_loop()
