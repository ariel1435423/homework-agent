from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from playwright.sync_api import TimeoutError, sync_playwright
from dotenv import load_dotenv
import json
import os
import re
import requests

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ModuleNotFoundError:
    BeautifulSoup = None
    HAS_BS4 = False

load_dotenv()

CET_HOST = "https://bagruthumanities.cet.ac.il"
CET_MY_URL = f"{CET_HOST}/my/"
PROFILE_DIR = os.path.join(os.getcwd(), "cet_profile")
ART_DIR = os.path.join(os.getcwd(), "artifacts")
OUT_DIR = os.path.join(os.getcwd(), "all_tasks")

MOE_USER = os.getenv("MOE_USERNAME", "").strip()
MOE_PASS = os.getenv("MOE_PASSWORD", "").strip()
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("CET_REQUEST_TIMEOUT", "20"))
COURSE_WORKERS = max(1, int(os.getenv("CET_COURSE_WORKERS", "6")))
DETAIL_WORKERS = max(1, int(os.getenv("CET_DETAIL_WORKERS", "6")))

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


def wait_ready(page, ms=1500):
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except TimeoutError:
        pass
    page.wait_for_timeout(ms)


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


def normalize_url(url):
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("/"):
        return f"{CET_HOST}{url}"
    return f"{CET_HOST}/{url.lstrip('/')}"


def extract_query_id(url):
    match = re.search(r"[?&]id=(\d+)", url or "")
    return match.group(1) if match else ""


def first_non_empty_locator_text(locator, selectors):
    for selector in selectors:
        try:
            element = locator.locator(selector).first
            text = clean(element.inner_text())
            if text:
                return text
        except Exception:
            continue
    return ""


def soup_text(node):
    if node is None:
        return ""
    return clean(node.get_text(" ", strip=True))


def extract_text_from_selectors(soup, selectors):
    for selector in selectors:
        node = soup.select_one(selector)
        text = soup_text(node)
        if text:
            return text
    return ""


def build_request_state(context, page):
    return {
        "headers": {
            "User-Agent": page.evaluate("() => navigator.userAgent"),
            "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
        },
        "cookies": context.cookies(),
    }


def build_http_session(request_state):
    session = requests.Session()
    session.headers.update(request_state["headers"])

    for cookie in request_state["cookies"]:
        try:
            session.cookies.set(
                cookie["name"],
                cookie["value"],
                domain=cookie.get("domain"),
                path=cookie.get("path") or "/",
            )
        except Exception:
            session.cookies.set(cookie["name"], cookie["value"])

    return session


def fetch_html(request_state, url):
    session = build_http_session(request_state)
    response = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
    response.raise_for_status()

    if "lgn.edu.gov.il" in response.url.lower():
        raise RuntimeError("CET session expired during HTTP crawl")

    return response.text


def is_logged_in_my(page):
    try:
        body = page.inner_text("body")
    except Exception:
        return False
    return any(token in body for token in ["My courses", "\u05d4\u05e7\u05d5\u05e8\u05e1\u05d9\u05dd", "\u05d4\u05d3\u05e3 \u05d4\u05e8\u05d0\u05e9\u05d9"])


def click_moe_login(page, ts):
    print("[CET] Looking for IDM login button...")
    page.wait_for_timeout(2500)

    for selector in ['a[onclick*="LoginMOE"]', '[onclick*="LoginMOE"]', 'a:has-text("IDM")']:
        try:
            button = page.locator(selector)
            if button.count() > 0:
                button.first.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                button.first.click()
                return True
        except Exception:
            continue

    save_debug(page, ts, "cet_login_button_missing")
    return False


def handle_moe_redirect(page, ts):
    try:
        page.wait_for_url("**lgn.edu.gov.il**", timeout=20000)
    except TimeoutError:
        save_debug(page, ts, "cet_moe_redirect_timeout")
        return False

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
        print("[CET] MOE login error:", exc)
        save_debug(page, ts, "cet_moe_login_failed")
        return False

    try:
        page.wait_for_url("**cet.ac.il**", timeout=30000)
    except TimeoutError:
        pass

    wait_ready(page, 2500)
    return True


def ensure_logged_in(page, ts):
    page.goto(CET_MY_URL, wait_until="domcontentloaded")
    wait_ready(page, 2000)

    if is_logged_in_my(page):
        print("[CET] Already logged in")
        return True

    if not click_moe_login(page, ts):
        return False

    if not handle_moe_redirect(page, ts):
        return False

    page.goto(CET_MY_URL, wait_until="domcontentloaded")
    wait_ready(page, 2500)

    if not is_logged_in_my(page):
        save_debug(page, ts, "cet_login_failed")
        return False

    print("[CET] Logged in!")
    return True


def parse_my_page_html(html):
    soup = BeautifulSoup(html, "html.parser")
    tasks = []
    course_urls = set()

    for card in soup.select('a.card.dashboard-card[href*="/mod/assign/view.php?id="]'):
        href = normalize_url(card.get("href") or "")
        title = clean(card.get("title") or soup_text(card))
        if not href or not title:
            continue

        tasks.append(
            {
                "source": "cet",
                "title": title,
                "course": "",
                "course_id": "",
                "url": href,
                "due_date": None,
                "days_left": None,
                "description": "",
            }
        )

    for link in soup.select('a.mcc_view[href*="/course/view.php?id="], a[href*="/course/view.php?id="]'):
        href = normalize_url(link.get("href") or "")
        if "/course/view.php?id=" in href:
            course_urls.add(href)

    return tasks, sorted(course_urls)


def parse_course_page_html(html, course_url):
    soup = BeautifulSoup(html, "html.parser")
    tasks = []
    course_name = extract_text_from_selectors(
        soup,
        [
            '.breadcrumb a[href*="/course/view.php?id="][aria-current="page"]',
            'nav a[href*="/course/view.php?id="][aria-current="page"]',
            '.breadcrumb a[href*="/course/view.php?id="]',
            'nav a[href*="/course/view.php?id="]',
            "#page-header h1",
            ".page-header-headings h1",
            "h1",
        ],
    )
    course_id = extract_query_id(course_url)

    for link in soup.select(
        'div.activity-item a.aalink.stretched-link[href*="/mod/assign/view.php?id="], '
        'div.activity-item a[href*="/mod/assign/view.php?id="]'
    ):
        container = link.find_parent("div", class_=lambda value: value and "activity-item" in value)
        href = normalize_url(link.get("href") or "")
        title = clean(soup_text(link.select_one(".instancename")) or soup_text(link))

        if not href or not title:
            continue

        description = clean((container or {}).get("data-activityname", "")) if container else ""
        if description == title:
            description = ""

        info_node = None
        if container:
            info_node = container.select_one('[data-region="activity-information"], .activity-information')
        due_date = parse_date(soup_text(info_node))

        tasks.append(
            {
                "source": "cet",
                "title": title,
                "course": course_name,
                "course_id": course_id,
                "url": href,
                "due_date": due_date,
                "days_left": days_until(due_date),
                "description": description[:200],
            }
        )

    return course_name or course_id, tasks


def parse_assignment_details_html(html, task):
    soup = BeautifulSoup(html, "html.parser")
    details = {
        "course": task.get("course", ""),
        "course_id": task.get("course_id", ""),
        "due_date": task.get("due_date"),
        "days_left": task.get("days_left"),
        "description": task.get("description", ""),
    }

    if not details["course"]:
        course_link = soup.select_one('.breadcrumb a[href*="/course/view.php?id="], nav a[href*="/course/view.php?id="]')
        details["course"] = soup_text(course_link)

    if not details["course_id"]:
        course_link = soup.select_one('.breadcrumb a[href*="/course/view.php?id="], nav a[href*="/course/view.php?id="]')
        details["course_id"] = extract_query_id(course_link.get("href") if course_link else "")

    if not details["description"]:
        for selector in ["#intro", ".activity-description", ".box.generalbox", ".formattedtext", "main p"]:
            text = extract_text_from_selectors(soup, [selector])
            if text and len(text) > 15:
                details["description"] = text[:200]
                break

    if not details["due_date"]:
        for row in soup.select("table.generaltable tr"):
            row_text = soup_text(row)
            if not row_text:
                continue

            if any(
                keyword in row_text.lower()
                for keyword in ["due", "deadline", "\u05de\u05d5\u05e2\u05d3", "\u05ea\u05d0\u05e8\u05d9\u05da", "\u05d4\u05d2\u05e9"]
            ):
                due_date = parse_date(row_text)
                if due_date:
                    details["due_date"] = due_date
                    details["days_left"] = days_until(due_date)
                    break

    if not details["due_date"]:
        body_text = soup_text(soup.body)
        for line in re.split(r"[\n\r]+", body_text):
            if any(
                keyword in line.lower()
                for keyword in ["due", "deadline", "\u05de\u05d5\u05e2\u05d3", "\u05ea\u05d0\u05e8\u05d9\u05da", "\u05d4\u05d2\u05e9"]
            ):
                due_date = parse_date(line)
                if due_date:
                    details["due_date"] = due_date
                    details["days_left"] = days_until(due_date)
                    break

    return details


def fetch_course_tasks(request_state, course_url):
    html = fetch_html(request_state, course_url)
    return parse_course_page_html(html, course_url)


def fetch_assignment_details(request_state, task):
    html = fetch_html(request_state, task["url"])
    return parse_assignment_details_html(html, task)


def should_fetch_details(task):
    return not task.get("course") or not task.get("description") or not task.get("due_date")


def collect_course_urls_browser(page):
    urls = set()

    for selector in ['a.mcc_view[href*="/course/view.php?id="]', 'a[href*="/course/view.php?id="]']:
        links = page.locator(selector)
        for index in range(min(links.count(), 200)):
            try:
                href = normalize_url(links.nth(index).get_attribute("href") or "")
            except Exception:
                continue
            if "/course/view.php?id=" in href:
                urls.add(href)

    return sorted(urls)


def extract_dashboard_tasks_browser(page):
    tasks = []
    cards = page.locator('a.card.dashboard-card[href*="/mod/assign/view.php?id="]')

    for index in range(cards.count()):
        card = cards.nth(index)
        try:
            href = normalize_url(card.get_attribute("href") or "")
        except Exception:
            href = ""

        if not href:
            continue

        title = clean(card.get_attribute("title") or "")
        if not title:
            title = clean(card.inner_text())

        if not title:
            continue

        tasks.append(
            {
                "source": "cet",
                "title": title,
                "course": "",
                "course_id": "",
                "url": href,
                "due_date": None,
                "days_left": None,
                "description": "",
            }
        )

    return tasks


def extract_tasks_from_course_browser(page, course_url):
    tasks = []
    page.goto(course_url, wait_until="domcontentloaded", timeout=30000)
    wait_ready(page, 1500)

    course_name = first_non_empty_locator_text(
        page,
        [
            '.breadcrumb a[href*="/course/view.php?id="][aria-current="page"]',
            'nav a[href*="/course/view.php?id="][aria-current="page"]',
            '.breadcrumb a[href*="/course/view.php?id="]',
            'nav a[href*="/course/view.php?id="]',
            "#page-header h1",
            ".page-header-headings h1",
            "h1",
        ],
    )
    course_id = extract_query_id(course_url)

    items = page.locator(
        'div.activity-item a.aalink.stretched-link[href*="/mod/assign/view.php?id="], '
        'div.activity-item a[href*="/mod/assign/view.php?id="]'
    )

    for index in range(items.count()):
        link = items.nth(index)
        container = link.locator('xpath=ancestor::div[contains(@class,"activity-item")][1]')

        try:
            href = normalize_url(link.get_attribute("href") or "")
        except Exception:
            href = ""

        if not href:
            continue

        title = first_non_empty_locator_text(link, [".instancename"])
        if not title:
            title = clean(link.inner_text())

        description = ""
        try:
            description = clean(container.get_attribute("data-activityname") or "")
        except Exception:
            description = ""
        if description == title:
            description = ""

        info_text = first_non_empty_locator_text(
            container,
            ['[data-region="activity-information"]', ".activity-information"],
        )
        due_date = parse_date(info_text)

        tasks.append(
            {
                "source": "cet",
                "title": title,
                "course": course_name,
                "course_id": course_id,
                "url": href,
                "due_date": due_date,
                "days_left": days_until(due_date),
                "description": description[:200],
            }
        )

    return course_name or course_id, tasks


def get_assignment_details_browser(page, task):
    details = {
        "course": task.get("course", ""),
        "course_id": task.get("course_id", ""),
        "due_date": task.get("due_date"),
        "days_left": task.get("days_left"),
        "description": task.get("description", ""),
    }

    try:
        page.goto(task["url"], wait_until="domcontentloaded", timeout=25000)
        wait_ready(page, 1500)
        body = page.inner_text("body")

        if not details["course"]:
            details["course"] = first_non_empty_locator_text(
                page,
                ['.breadcrumb a[href*="/course/view.php?id="]', 'nav a[href*="/course/view.php?id="]'],
            )

        if not details["course_id"]:
            try:
                course_href = page.locator('.breadcrumb a[href*="/course/view.php?id="]').first.get_attribute("href") or ""
            except Exception:
                course_href = ""
            details["course_id"] = extract_query_id(course_href)

        if not details["description"]:
            for selector in ["#intro", ".activity-description", ".box.generalbox", ".formattedtext", "main p"]:
                try:
                    text = clean(page.locator(selector).first.inner_text())
                except Exception:
                    text = ""
                if text and len(text) > 15:
                    details["description"] = text[:200]
                    break

        if not details["due_date"]:
            rows = page.locator("table.generaltable tr")
            for index in range(rows.count()):
                try:
                    row_text = clean(rows.nth(index).inner_text())
                except Exception:
                    row_text = ""
                if not row_text:
                    continue
                if any(keyword in row_text.lower() for keyword in ["due", "deadline", "\u05de\u05d5\u05e2\u05d3", "\u05ea\u05d0\u05e8\u05d9\u05da", "\u05d4\u05d2\u05e9"]):
                    due_date = parse_date(row_text)
                    if due_date:
                        details["due_date"] = due_date
                        details["days_left"] = days_until(due_date)
                        break

        if not details["due_date"]:
            for line in re.split(r"[\n\r]+", body):
                if any(keyword in line.lower() for keyword in ["due", "deadline", "\u05de\u05d5\u05e2\u05d3", "\u05ea\u05d0\u05e8\u05d9\u05da", "\u05d4\u05d2\u05e9"]):
                    due_date = parse_date(line)
                    if due_date:
                        details["due_date"] = due_date
                        details["days_left"] = days_until(due_date)
                        break
    except Exception as exc:
        print(f"[CET] Details failed for {task['url']}: {exc}")

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


def merge_task_details(task, details):
    for key, value in details.items():
        if value and not task.get(key):
            task[key] = value

    if task.get("due_date") and task.get("days_left") is None:
        task["days_left"] = days_until(task["due_date"])


def extract_tasks_http(request_state, my_page_html):
    print("[CET] Extracting assignments...")

    dashboard_tasks, course_urls = parse_my_page_html(my_page_html)
    if dashboard_tasks:
        print(f"[CET] Dashboard assignments: {len(dashboard_tasks)}")
    print(f"[CET] Course pages discovered: {len(course_urls)}")

    all_tasks = list(dashboard_tasks)

    if course_urls:
        with ThreadPoolExecutor(max_workers=min(COURSE_WORKERS, len(course_urls))) as executor:
            future_to_url = {
                executor.submit(fetch_course_tasks, request_state, course_url): course_url
                for course_url in course_urls
            }
            for future in as_completed(future_to_url):
                course_url = future_to_url[future]
                try:
                    course_name, tasks = future.result()
                    if tasks:
                        print(f"[CET] Course {course_name}: {len(tasks)} assignments")
                    all_tasks.extend(tasks)
                except Exception as exc:
                    print(f"[CET] Failed to scan {course_url}: {exc}")

    tasks = dedupe_tasks(all_tasks)
    print(f"[CET] Unique assignments before details: {len(tasks)}")

    detail_candidates = [task for task in tasks if should_fetch_details(task)]
    if detail_candidates:
        print(f"[CET] Fetching details for {len(detail_candidates)} assignments with {min(DETAIL_WORKERS, len(detail_candidates))} workers")
        with ThreadPoolExecutor(max_workers=min(DETAIL_WORKERS, len(detail_candidates))) as executor:
            future_to_task = {
                executor.submit(fetch_assignment_details, request_state, task): task
                for task in detail_candidates
            }
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    merge_task_details(task, future.result())
                except Exception as exc:
                    print(f"[CET] Details failed for {task['url']}: {exc}")

    return tasks


def extract_tasks_browser(page):
    print("[CET] bs4 not installed, using Playwright fallback")
    print("[CET] Extracting assignments...")

    dashboard_tasks = extract_dashboard_tasks_browser(page)
    course_urls = collect_course_urls_browser(page)

    if dashboard_tasks:
        print(f"[CET] Dashboard assignments: {len(dashboard_tasks)}")
    print(f"[CET] Course pages discovered: {len(course_urls)}")

    all_tasks = list(dashboard_tasks)

    for course_url in course_urls:
        try:
            course_name, tasks = extract_tasks_from_course_browser(page, course_url)
            if tasks:
                print(f"[CET] Course {course_name}: {len(tasks)} assignments")
            all_tasks.extend(tasks)
        except Exception as exc:
            print(f"[CET] Failed to scan {course_url}: {exc}")

    tasks = dedupe_tasks(all_tasks)
    print(f"[CET] Unique assignments before details: {len(tasks)}")

    for task in tasks:
        if should_fetch_details(task):
            merge_task_details(task, get_assignment_details_browser(page, task))

    return tasks


def main():
    if not MOE_USER or not MOE_PASS:
        print("[CET] Missing MOE credentials")
        return []

    ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as playwright:
        args = ["--disable-blink-features=AutomationControlled"]
        if HEADLESS:
            args += ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        else:
            args += ["--start-maximized"]

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=HEADLESS,
            args=args,
            viewport={"width": 1600, "height": 900},
        )
        page = context.new_page()

        if not ensure_logged_in(page, ts):
            print("[CET] Login failed")
            context.close()
            return []

        save_debug(page, ts, "cet_my_page")

        if HAS_BS4:
            my_page_html = page.content()
            request_state = build_request_state(context, page)
            context.close()
            tasks = extract_tasks_http(request_state, my_page_html)
        else:
            tasks = extract_tasks_browser(page)
            context.close()

        out_path = os.path.join(OUT_DIR, f"cet_tasks_{ts}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)

        print(f"[CET] Found {len(tasks)} tasks -> {out_path}")
        return tasks


if __name__ == "__main__":
    main()
