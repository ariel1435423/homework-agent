from playwright.sync_api import TimeoutError, sync_playwright
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import os
import re

from playwright_context import close_browser_context, launch_browser_context

load_dotenv()

PROFILE_DIR = os.getenv("CLASSROOM_PROFILE_DIR", os.path.join(os.getcwd(), "chrome_profile"))
ART_DIR = os.path.join(os.getcwd(), "artifacts")
OUT_DIR = os.path.join(os.getcwd(), "all_tasks")
TODO_URL = "https://classroom.google.com/u/0/a/not-turned-in/all"
CLASSROOM_BASE_URL = "https://classroom.google.com"

MOE_USER = os.getenv("MOE_USERNAME", "").strip()
MOE_PASS = os.getenv("MOE_PASSWORD", "").strip()
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

MONTHS = {
    "\u05d9\u05e0\u05d5\u05d0\u05e8": "01",
    "\u05d9\u05e0\u05d5": "01",
    "\u05e4\u05d1\u05e8\u05d5\u05d0\u05e8": "02",
    "\u05e4\u05d1\u05e8": "02",
    "\u05de\u05e8\u05e5": "03",
    "\u05d0\u05e4\u05e8\u05d9\u05dc": "04",
    "\u05d0\u05e4\u05e8": "04",
    "\u05de\u05d0\u05d9": "05",
    "\u05d9\u05d5\u05e0\u05d9": "06",
    "\u05d9\u05d5\u05e0": "06",
    "\u05d9\u05d5\u05dc\u05d9": "07",
    "\u05d9\u05d5\u05dc": "07",
    "\u05d0\u05d5\u05d2\u05d5\u05e1\u05d8": "08",
    "\u05d0\u05d5\u05d2": "08",
    "\u05e1\u05e4\u05d8\u05de\u05d1\u05e8": "09",
    "\u05e1\u05e4\u05d8": "09",
    "\u05d0\u05d5\u05e7\u05d8\u05d5\u05d1\u05e8": "10",
    "\u05d0\u05d5\u05e7": "10",
    "\u05e0\u05d5\u05d1\u05de\u05d1\u05e8": "11",
    "\u05e0\u05d5\u05d1": "11",
    "\u05d3\u05e6\u05de\u05d1\u05e8": "12",
    "\u05d3\u05e6\u05de": "12",
    "january": "01",
    "jan": "01",
    "february": "02",
    "feb": "02",
    "march": "03",
    "mar": "03",
    "april": "04",
    "apr": "04",
    "may": "05",
    "june": "06",
    "jun": "06",
    "july": "07",
    "jul": "07",
    "august": "08",
    "aug": "08",
    "september": "09",
    "sep": "09",
    "october": "10",
    "oct": "10",
    "november": "11",
    "nov": "11",
    "december": "12",
    "dec": "12",
}

RELATIVE_DATE_OFFSETS = {
    "\u05d4\u05d9\u05d5\u05dd": 0,
    "\u05de\u05d7\u05e8": 1,
}


def clean(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def ensure_dirs():
    os.makedirs(ART_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)


def save_debug(page, ts, name):
    ensure_dirs()
    try:
        page.screenshot(path=os.path.join(ART_DIR, f"{name}_{ts}.png"), full_page=True)
        with open(os.path.join(ART_DIR, f"{name}_{ts}.html"), "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception:
        pass


def normalize_month_token(token):
    return (
        (token or "")
        .strip()
        .lower()
        .replace("\u05f3", "")
        .replace("\u05f4", "")
        .replace('"', "")
        .replace("'", "")
    )


def format_date(value):
    return value.strftime("%d/%m/%Y")


def parse_date(text, reference=None):
    text = clean(text)
    if not text:
        return None

    reference = reference or datetime.now()

    numeric = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b", text)
    if numeric:
        day, month, year = numeric.groups()
        year = int(year)
        if year < 100:
            year += 2000
        return f"{int(day):02d}/{int(month):02d}/{year:04d}"

    iso = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso:
        year, month, day = iso.groups()
        return f"{int(day):02d}/{int(month):02d}/{int(year):04d}"

    for token, offset in RELATIVE_DATE_OFFSETS.items():
        if token in text:
            return format_date(reference + timedelta(days=offset))

    month_match = re.search(
        r"(\d{1,2})\s+[\u05d1]?(?P<month>[\u05d0-\u05eaA-Za-z]{2,12})(?:[\s,]+(?P<year>\d{4}))?",
        text,
    )
    if month_match:
        day = int(month_match.group(1))
        month_token = normalize_month_token(month_match.group("month"))
        month = MONTHS.get(month_token)
        if month:
            year = month_match.group("year")
            if year is None:
                candidate = datetime(reference.year, int(month), day)
                if candidate.date() < reference.date() - timedelta(days=180):
                    candidate = datetime(reference.year + 1, int(month), day)
                return format_date(candidate)
            return f"{day:02d}/{int(month):02d}/{int(year):04d}"

    return None


def parse_due_date_text(text, reference=None):
    return parse_date(text, reference=reference)


def days_until(date_str):
    if not date_str:
        return None

    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"):
        try:
            due_date = datetime.strptime(date_str, fmt).date()
            return (due_date - datetime.now().date()).days
        except ValueError:
            continue

    return None


def is_old_task(task):
    days = task.get("days_left")
    return days is not None and days < -30


def make_absolute_url(url):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"{CLASSROOM_BASE_URL}{url}"


def first_non_empty_text(locator, selectors):
    for selector in selectors:
        try:
            element = locator.locator(selector).first
            text = clean(element.inner_text())
            if text:
                return text
        except Exception:
            continue
    return ""


def handle_moe_login(page, ts):
    print("[Classroom] MOE login...")
    try:
        page.wait_for_url("**lgn.edu.gov.il**", timeout=15000)
    except TimeoutError:
        pass

    page.wait_for_timeout(2000)

    try:
        page.locator("#userName").wait_for(state="visible", timeout=10000)
        page.locator("#userName").click()
        page.locator("#userName").fill(MOE_USER)
        page.locator("#password").wait_for(state="visible", timeout=10000)
        page.locator("#password").click()
        page.locator("#password").evaluate("(element) => element.removeAttribute('readonly')")
        page.locator("#password").fill(MOE_PASS)
        page.locator("#password").press("Enter")
    except Exception as exc:
        print("[Classroom] MOE error:", exc)
        save_debug(page, ts, "classroom_moe_login_failed")
        return False

    try:
        page.wait_for_url("**google.com**", timeout=30000)
    except TimeoutError:
        pass

    page.wait_for_timeout(3000)
    return True


def ensure_logged_in(page, ts):
    page.goto("https://classroom.google.com/u/0/h", wait_until="domcontentloaded")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except TimeoutError:
        pass

    page.wait_for_timeout(2000)

    if "lgn.edu.gov.il" in page.url or "accounts.google.com" in page.url:
        if "accounts.google.com" in page.url:
            for selector in [
                '[data-identifier]',
                'button:has-text("Next")',
                'button:has-text("\u05d4\u05de\u05e9\u05da")',
            ]:
                try:
                    candidate = page.locator(selector)
                    if candidate.count() > 0:
                        candidate.first.click()
                        page.wait_for_timeout(2000)
                        break
                except Exception:
                    continue

        if "lgn.edu.gov.il" not in page.url:
            try:
                page.wait_for_url("**lgn.edu.gov.il**", timeout=15000)
            except TimeoutError:
                save_debug(page, ts, "classroom_account_chooser")
                return False

        if not handle_moe_login(page, ts):
            return False

        page.goto("https://classroom.google.com/u/0/h", wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except TimeoutError:
            pass
        page.wait_for_timeout(3000)

    if "lgn.edu.gov.il" in page.url or "accounts.google.com" in page.url:
        save_debug(page, ts, "classroom_login_failed")
        return False

    print("[Classroom] Logged in!")
    return True


def expand_todo_sections(page):
    for _ in range(3):
        buttons = page.locator('div[data-id] button[aria-controls][aria-expanded="false"]:not([disabled])')
        count = buttons.count()
        if count == 0:
            return

        for index in range(count):
            try:
                buttons.nth(index).click()
                page.wait_for_timeout(350)
            except Exception:
                continue


def extract_card_tasks(page):
    tasks = []
    cards = page.locator('ol[jsname="g9rjof"] > li')

    for index in range(cards.count()):
        card = cards.nth(index)
        link = card.locator('a.nUg0Te[href*="/details"]').first

        try:
            href = link.get_attribute("href") or ""
        except Exception:
            href = ""

        if not href:
            continue

        title = first_non_empty_text(card, ["p.oDLUVd", 'p[class*="oDLUVd"]'])
        course = first_non_empty_text(card, ["p.tWeh6", 'p[class*="tWeh6"]'])
        due_text = first_non_empty_text(card, ["p.pOf0gc", 'p[class*="pOf0gc"]'])

        if not due_text:
            parts = []
            for part_index in range(card.locator('div.nQaZq p, div[class*="nQaZq"] p').count()):
                try:
                    part_text = clean(card.locator('div.nQaZq p, div[class*="nQaZq"] p').nth(part_index).inner_text())
                except Exception:
                    part_text = ""
                if part_text:
                    parts.append(part_text)
            due_text = ", ".join(parts)

        if not title:
            title = clean(link.inner_text())

        due_date = parse_due_date_text(due_text)

        task = {
            "source": "classroom",
            "title": title,
            "course": course,
            "url": make_absolute_url(href),
            "due_date": due_date,
            "days_left": days_until(due_date),
            "description": "",
        }

        if task["title"]:
            tasks.append(task)

    return dedupe_tasks(tasks)


def extract_fallback_tasks(page):
    tasks = []
    links = page.locator('a[href*="/details"]')

    for index in range(min(links.count(), 100)):
        link = links.nth(index)

        try:
            href = link.get_attribute("href") or ""
            title = clean(link.inner_text())
        except Exception:
            continue

        if not href or not title:
            continue

        tasks.append(
            {
                "source": "classroom",
                "title": title,
                "course": "",
                "url": make_absolute_url(href),
                "due_date": None,
                "days_left": None,
                "description": "",
            }
        )

    return dedupe_tasks(tasks)


def get_assignment_details(page, url):
    details = {"due_date": None, "days_left": None, "description": ""}

    try:
        page.goto(make_absolute_url(url), wait_until="domcontentloaded", timeout=25000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except TimeoutError:
            pass

        page.wait_for_timeout(1500)
        body = clean(page.inner_text("body"))

        due_date = None
        for line in re.split(r"[\n\r]+", body):
            if any(keyword in line.lower() for keyword in ["due", "deadline", "\u05de\u05d5\u05e2\u05d3", "\u05d4\u05d2\u05e9", "\u05ea\u05d0\u05e8\u05d9\u05da"]):
                due_date = parse_due_date_text(line)
                if due_date:
                    break

        if not due_date:
            due_date = parse_due_date_text(body)

        details["due_date"] = due_date
        details["days_left"] = days_until(due_date)

        for selector in [
            "main p",
            '[role="main"] p',
            'main div[dir="auto"]',
            '[role="main"] div[dir="auto"]',
        ]:
            nodes = page.locator(selector)
            for index in range(min(nodes.count(), 20)):
                try:
                    text = clean(nodes.nth(index).inner_text())
                except Exception:
                    text = ""

                if (
                    len(text) > 20
                    and "\u05e1\u05d9\u05de\u05d5\u05df \u05db'\u05d1\u05d5\u05e6\u05e2\u05d4'" not in text
                    and "\u05ea\u05d2\u05d5\u05d1\u05d5\u05ea \u05e4\u05e8\u05d8\u05d9\u05d5\u05ea" not in text
                ):
                    details["description"] = text[:200]
                    return details
    except Exception as exc:
        print(f"  [Classroom details error] {exc}")

    return details


def dedupe_tasks(tasks):
    merged = {}

    for task in tasks:
        url = task.get("url", "")
        if not url:
            continue

        existing = merged.get(url)
        if not existing:
            merged[url] = dict(task)
            continue

        for key, value in task.items():
            if key == "days_left":
                continue
            if value and not existing.get(key):
                existing[key] = value

        if existing.get("due_date") and existing.get("days_left") is None:
            existing["days_left"] = days_until(existing["due_date"])

    return list(merged.values())


def extract_tasks(page, ts):
    page.goto(TODO_URL, wait_until="domcontentloaded")

    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except TimeoutError:
        pass

    try:
        page.wait_for_selector('a.nUg0Te[href*="/details"], ol[jsname="g9rjof"]', timeout=15000)
    except TimeoutError:
        save_debug(page, ts, "classroom_todo_timeout")

    page.wait_for_timeout(2000)
    expand_todo_sections(page)
    page.wait_for_timeout(1000)
    save_debug(page, ts, "classroom_todo")

    tasks = extract_card_tasks(page)
    if not tasks:
        print("[Classroom] Card extraction returned 0 tasks, using fallback link extraction")
        tasks = extract_fallback_tasks(page)

    missing_due = [task for task in tasks if not task.get("due_date")]
    if missing_due:
        print(f"[Classroom] Filling missing due dates for {len(missing_due)} tasks...")

    for task in missing_due[:10]:
        details = get_assignment_details(page, task["url"])
        if details["due_date"] and not task.get("due_date"):
            task["due_date"] = details["due_date"]
            task["days_left"] = details["days_left"]
        if details["description"] and not task.get("description"):
            task["description"] = details["description"]

    before = len(tasks)
    tasks = [task for task in tasks if not is_old_task(task)]
    filtered = before - len(tasks)
    if filtered > 0:
        print(f"[Classroom] Filtered out {filtered} old tasks")

    return tasks


def main():
    if not MOE_USER or not MOE_PASS:
        print("[Classroom] Missing credentials")
        return []

    ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as playwright:
        args = ["--disable-blink-features=AutomationControlled"]
        if HEADLESS:
            args += ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        else:
            args += ["--start-maximized"]

        browser, context = launch_browser_context(
            playwright,
            profile_dir=PROFILE_DIR,
            headless=HEADLESS,
            args=args,
            viewport={"width": 1600, "height": 900},
            label="Classroom",
        )
        page = context.new_page()

        try:
            if not ensure_logged_in(page, ts):
                print("[Classroom] Login failed")
                return []

            tasks = extract_tasks(page, ts)

            out_path = os.path.join(OUT_DIR, f"classroom_tasks_{ts}.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)

            print(f"[Classroom] Found {len(tasks)} tasks -> {out_path}")
            return tasks
        finally:
            close_browser_context(browser, context)


if __name__ == "__main__":
    main()
