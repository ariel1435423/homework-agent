import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime

from dotenv import load_dotenv

from supabase_sync import sync_tasks_to_supabase

load_dotenv()

OUT_DIR = os.path.join(os.getcwd(), "all_tasks")
ART_DIR = os.path.join(os.getcwd(), "artifacts")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ART_DIR, exist_ok=True)

KEEP_ALL_TASK_HISTORY = max(1, int(os.getenv("KEEP_ALL_TASK_HISTORY", "5")))
KEEP_ARTIFACT_RUNS = max(1, int(os.getenv("KEEP_ARTIFACT_RUNS", "2")))
STALE_TASK_DAYS = max(1, int(os.getenv("STALE_TASK_DAYS", "30")))
KEEP_COMPLETED_TASKS = os.getenv("KEEP_COMPLETED_TASKS", "false").lower() == "true"
KEEP_CLOSED_TASKS = os.getenv("KEEP_CLOSED_TASKS", "false").lower() == "true"

SCRAPERS = [
    {
        "name": "Google Classroom",
        "script": "classroom_todo.py",
        "env": {
            "CLASSROOM_PROFILE_DIR": os.path.join(os.getcwd(), "chrome_profile"),
        },
    },
    {
        "name": "Moodle (Mashov)",
        "script": "moodle_extract_tasks.py",
        "env": {
            "MOODLE_PROFILE_DIR": os.path.join(os.getcwd(), "moodle_profile"),
        },
    },
    {
        "name": "CET (Nativ Digital)",
        "script": "cet_extract_tasks.py",
        "env": {},
    },
]


def cleanup_intermediate_tasks() -> int:
    patterns = [
        "classroom_tasks_*.json",
        "moodle_tasks_*.json",
        "cet_tasks_*.json",
    ]

    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(OUT_DIR, pattern)))

    if not files:
        print("  (no intermediate files to clean)")
        return 0

    for path in files:
        os.remove(path)
        print(f"  Deleted intermediate: {os.path.basename(path)}")

    print(f"  Cleaned {len(files)} intermediate file(s) from all_tasks/")
    return len(files)


def extract_run_timestamp(path: str) -> str | None:
    match = re.search(r"_(\d{8}_\d{6})(?:\.[^.]+)?$", os.path.basename(path))
    return match.group(1) if match else None


def cleanup_old_history(pattern: str, keep_last: int, label: str) -> int:
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    stale_files = files[keep_last:]

    if not stale_files:
        print(f"  (no old {label} files to clean)")
        return 0

    for path in stale_files:
        os.remove(path)
        print(f"  Deleted old {label}: {os.path.basename(path)}")

    return len(stale_files)


def cleanup_old_artifacts(keep_runs: int) -> int:
    artifact_files = [
        os.path.join(ART_DIR, name)
        for name in os.listdir(ART_DIR)
        if os.path.isfile(os.path.join(ART_DIR, name))
    ]

    timestamped_artifacts = {}
    for path in artifact_files:
        ts = extract_run_timestamp(path)
        if not ts:
            continue
        timestamped_artifacts.setdefault(ts, []).append(path)

    if not timestamped_artifacts:
        print("  (no timestamped artifacts to clean)")
        return 0

    kept_timestamps = set(sorted(timestamped_artifacts.keys(), reverse=True)[:keep_runs])
    deleted = 0

    for ts, paths in sorted(timestamped_artifacts.items(), reverse=True):
        if ts in kept_timestamps:
            continue
        for path in paths:
            os.remove(path)
            deleted += 1
            print(f"  Deleted old artifact: {os.path.basename(path)}")

    if deleted == 0:
        print("  (no old artifacts to clean)")

    return deleted


def cleanup_old_output_files() -> None:
    print("Cleaning old all_tasks history...")
    removed_history = cleanup_old_history(
        os.path.join(OUT_DIR, "all_tasks_*.json"),
        KEEP_ALL_TASK_HISTORY,
        "all_tasks history",
    )
    print(f"  Removed {removed_history} old history file(s)")

    print("Cleaning old artifacts...")
    removed_artifacts = cleanup_old_artifacts(KEEP_ARTIFACT_RUNS)
    print(f"  Removed {removed_artifacts} old artifact file(s)")


def run_script(name: str, script: str) -> int:
    print(f"\n{'=' * 40}")
    print(f"Running {name}...")
    print(f"{'=' * 40}")

    result = subprocess.run(
        [sys.executable, script],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"WARNING: {name} finished with errors (code {result.returncode})")
    else:
        print(f"OK: {name} done")

    return result.returncode


def run_scripts_parallel(scrapers) -> dict[str, int]:
    print(f"\n{'=' * 50}")
    print("Starting scrapers in parallel...")
    print("=" * 50)

    processes = []
    for scraper in scrapers:
        env = os.environ.copy()
        env.update(scraper.get("env", {}))

        print(f"Launching {scraper['name']}...")
        process = subprocess.Popen(
            [sys.executable, scraper["script"]],
            env=env,
        )
        processes.append((scraper["name"], process))

    results = {}
    for name, process in processes:
        code = process.wait()
        results[name] = code

        if code != 0:
            print(f"WARNING: {name} finished with errors (code {code})")
        else:
            print(f"OK: {name} done")

    return results


def load_latest_json(pattern: str, min_mtime: float | None = None):
    files = glob.glob(pattern)
    if min_mtime is not None:
        files = [path for path in files if os.path.getmtime(path) >= min_mtime]

    if not files:
        return []

    latest = max(files, key=os.path.getmtime)
    print(f"  Loading: {latest}")

    try:
        with open(latest, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"  Error loading {latest}: {exc}")
        return []


def normalize_task_status(task: dict) -> str:
    raw_status = str(task.get("status", "")).strip().lower()
    normalized_statuses = {
        "active": "active",
        "pending": "active",
        "open": "active",
        "late": "late",
        "overdue": "late",
        "completed": "completed",
        "done": "completed",
        "submitted": "completed",
        "closed": "closed",
        "stale": "stale",
    }
    if raw_status in normalized_statuses:
        return normalized_statuses[raw_status]

    haystack = " | ".join(
        str(task.get(key, "")).strip().lower()
        for key in ("status", "title", "description", "course")
    )

    completed_tokens = [
        "הוגש",
        "הושלם",
        "בוצע",
        "submitted",
        "turned in",
        "completed",
        "done",
        "graded",
    ]
    closed_tokens = [
        "לא ניתן להגיש",
        "ההגשה נסגרה",
        "נסגר",
        "פג תוקף",
        "closed",
        "submission closed",
        "unavailable",
    ]

    if any(token in haystack for token in completed_tokens):
        return "completed"
    if any(token in haystack for token in closed_tokens):
        return "closed"

    days_left = task.get("days_left")
    if isinstance(days_left, str):
        try:
            days_left = int(days_left)
        except ValueError:
            days_left = None

    if isinstance(days_left, int) and days_left < -STALE_TASK_DAYS:
        return "stale"

    return "active"


def filter_relevant_tasks(tasks: list[dict]) -> tuple[list[dict], dict[str, int]]:
    filtered = []
    removed_counts: dict[str, int] = {}

    for task in tasks:
        normalized = dict(task)
        normalized["status"] = normalize_task_status(normalized)

        status = normalized["status"]
        keep = True
        if status == "completed" and not KEEP_COMPLETED_TASKS:
            keep = False
        elif status in {"closed", "stale"} and not KEEP_CLOSED_TASKS:
            keep = False

        if keep:
            filtered.append(normalized)
        else:
            removed_counts[status] = removed_counts.get(status, 0) + 1

    return filtered, removed_counts


def main() -> None:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_started_at = datetime.now().timestamp() - 5

    print("=" * 50)
    print("Homework Agent - Starting all scrapers")
    print(f"Time: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)

    scraper_results = run_scripts_parallel(SCRAPERS)

    print(f"\n{'=' * 50}")
    print("Combining all results...")

    classroom_tasks = load_latest_json(os.path.join(OUT_DIR, "classroom_tasks_*.json"), min_mtime=run_started_at)

    moodle_tasks = load_latest_json(os.path.join(OUT_DIR, "moodle_tasks_*.json"), min_mtime=run_started_at)

    cet_tasks = load_latest_json(os.path.join(OUT_DIR, "cet_tasks_*.json"), min_mtime=run_started_at)

    for task in classroom_tasks:
        task.setdefault("source", "classroom")
    for task in moodle_tasks:
        task.setdefault("source", "moodle")
    for task in cet_tasks:
        task.setdefault("source", "cet")

    all_tasks = classroom_tasks + moodle_tasks + cet_tasks
    all_tasks, removed_counts = filter_relevant_tasks(all_tasks)

    combined_path = os.path.join(OUT_DIR, f"all_tasks_{ts}.json")
    with open(combined_path, "w", encoding="utf-8") as f:
        json.dump(all_tasks, f, ensure_ascii=False, indent=2)

    supabase_result = sync_tasks_to_supabase(
        all_tasks,
        run_key=ts,
        scraper_results=scraper_results,
        combined_path=combined_path,
    )

    print(f"\n{'=' * 50}")
    print("DONE")
    print(f"Classroom: {len(classroom_tasks)} tasks")
    print(f"Moodle:    {len(moodle_tasks)} tasks")
    print(f"CET:       {len(cet_tasks)} tasks")
    print(f"Total:     {len(all_tasks)} tasks")
    print(f"Saved to:  {combined_path}")
    if removed_counts:
        removed_summary = ", ".join(f"{status}={count}" for status, count in sorted(removed_counts.items()))
        print(f"Filtered:  {removed_summary}")
    if supabase_result["status"] == "success":
        print(f"Supabase:  synced {supabase_result['uploaded_tasks']} tasks")
    elif supabase_result["status"] == "skipped":
        print("Supabase:  skipped (missing config)")
    else:
        print(f"Supabase:  error - {supabase_result['error']}")
    print("=" * 50)

    if all_tasks:
        print("\nAll tasks:")
        for task in all_tasks:
            source = task.get("source", "?")
            title = task.get("title", "?")
            url = task.get("url", "")
            print(f"  [{source}] {title}")
            if url:
                print(f"      {url[:100]}")

    print(f"\n{'=' * 50}")
    print("Cleaning up files...")
    cleanup_intermediate_tasks()
    cleanup_old_output_files()
    print("=" * 50)


if __name__ == "__main__":
    main()
