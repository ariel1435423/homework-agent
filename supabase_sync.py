import hashlib
import json
import os
from datetime import UTC, datetime
from urllib.parse import parse_qs, unquote, urlencode, urlparse, urlunparse

import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_SECRET_KEY", "").strip()
)
SUPABASE_TIMEOUT_SEC = max(5, int(os.getenv("SUPABASE_TIMEOUT_SEC", "20")))

KNOWN_TASK_FIELDS = {
    "source",
    "title",
    "course",
    "course_id",
    "url",
    "due_date",
    "days_left",
    "description",
    "grade",
}


def is_supabase_configured():
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def utc_now_iso():
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_text(value):
    return " ".join(str(value or "").split())


def parse_due_date(date_str):
    if not date_str:
        return None

    value = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def canonicalize_url(source, url):
    if not url:
        return ""

    parsed = urlparse(url)
    if source == "moodle":
        query = parse_qs(parsed.query)
        wants_url = query.get("wantsurl", [None])[0]
        school_slug = parsed.path.strip("/").split("/")[0] if parsed.path.strip("/") else ""
        if wants_url:
            wants_parsed = urlparse(unquote(wants_url))
            canonical_path = f"/{school_slug}/{wants_parsed.path.lstrip('/')}" if school_slug else wants_parsed.path
            return urlunparse((parsed.scheme, parsed.netloc, canonical_path, "", wants_parsed.query, ""))

    filtered_query = []
    for key, values in parse_qs(parsed.query, keep_blank_values=True).items():
        if key.lower() in {"mp", "token", "ts", "timestamp"}:
            continue
        for value in values:
            filtered_query.append((key, value))

    query_string = urlencode(sorted(filtered_query), doseq=True)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query_string, ""))


def build_task_key(task):
    identity = {
        "source": normalize_text(task.get("source")),
        "title": normalize_text(task.get("title")),
        "course": normalize_text(task.get("course")),
        "course_id": normalize_text(task.get("course_id")),
        "canonical_url": canonicalize_url(task.get("source"), task.get("url")),
        "due_date": normalize_text(task.get("due_date")),
    }
    payload = json.dumps(identity, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_task_record(task, run_id):
    source = normalize_text(task.get("source"))
    metadata = {k: v for k, v in task.items() if k not in KNOWN_TASK_FIELDS}

    return {
        "task_key": build_task_key(task),
        "source": source,
        "title": normalize_text(task.get("title")),
        "course": normalize_text(task.get("course")),
        "course_id": normalize_text(task.get("course_id")) or None,
        "url": task.get("url") or None,
        "canonical_url": canonicalize_url(source, task.get("url")) or None,
        "due_date": parse_due_date(task.get("due_date")),
        "due_date_raw": task.get("due_date") or None,
        "days_left": task.get("days_left"),
        "description": normalize_text(task.get("description")) or None,
        "grade": normalize_text(task.get("grade")) or None,
        "is_active": True,
        "last_seen_at": utc_now_iso(),
        "last_seen_run_id": run_id,
        "metadata": metadata,
        "raw_task": task,
    }


def dedupe_task_records(records):
    deduped = {}
    for record in records:
        deduped[record["task_key"]] = record
    return list(deduped.values())


def chunked(items, size):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def build_headers(prefer=None):
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def postgrest_request(method, path, *, params=None, json_body=None, prefer=None):
    response = requests.request(
        method=method,
        url=f"{SUPABASE_URL}/rest/v1/{path}",
        headers=build_headers(prefer=prefer),
        params=params,
        json=json_body,
        timeout=SUPABASE_TIMEOUT_SEC,
    )
    response.raise_for_status()
    if response.content:
        return response.json()
    return None


def create_run_record(run_key, task_count, scraper_results, combined_path):
    source_counts = {}
    for source in ["classroom", "moodle", "cet"]:
        source_counts[source] = 0

    status = "completed"
    if any(code != 0 for code in scraper_results.values()):
        status = "completed_with_errors"

    payload = {
        "run_key": run_key,
        "status": status,
        "task_count": task_count,
        "source_counts": source_counts,
        "scraper_results": scraper_results,
        "combined_path": combined_path,
        "finished_at": utc_now_iso(),
    }
    rows = postgrest_request(
        "POST",
        "scraper_runs",
        json_body=payload,
        prefer="return=representation",
    )
    return rows[0]


def update_run_source_counts(run_id, tasks):
    source_counts = {}
    for task in tasks:
        source = task.get("source", "unknown")
        source_counts[source] = source_counts.get(source, 0) + 1

    postgrest_request(
        "PATCH",
        "scraper_runs",
        params={"id": f"eq.{run_id}"},
        json_body={"source_counts": source_counts},
        prefer="return=minimal",
    )


def upsert_tasks(records):
    if not records:
        return

    for batch in chunked(records, 200):
        postgrest_request(
            "POST",
            "tasks",
            params={"on_conflict": "task_key"},
            json_body=batch,
            prefer="resolution=merge-duplicates,return=minimal",
        )


def deactivate_stale_tasks(run_id):
    postgrest_request(
        "PATCH",
        "tasks",
        params={
            "is_active": "eq.true",
            "last_seen_run_id": f"neq.{run_id}",
        },
        json_body={"is_active": False},
        prefer="return=minimal",
    )


def sync_tasks_to_supabase(tasks, run_key, scraper_results, combined_path, deactivate_missing=True):
    if not is_supabase_configured():
        return {"status": "skipped", "reason": "missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY"}

    try:
        run_row = create_run_record(run_key, len(tasks), scraper_results, combined_path)
        records = dedupe_task_records([build_task_record(task, run_row["id"]) for task in tasks])

        update_run_source_counts(run_row["id"], records)
        upsert_tasks(records)

        if deactivate_missing and scraper_results and all(code == 0 for code in scraper_results.values()):
            deactivate_stale_tasks(run_row["id"])

        return {
            "status": "success",
            "run_id": run_row["id"],
            "uploaded_tasks": len(records),
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }
