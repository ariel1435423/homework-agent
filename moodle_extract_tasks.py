# moodle_extract_tasks.py — v3
# גרסה מפושטת: קורא משימות ישירות מדף "משימות Moodle" של Mashov
# בלי SSO ל-Moodle! הרבה יותר מהיר ופשוט.
from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
from datetime import datetime
import os, json, re

load_dotenv()

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")
ART_DIR = os.path.join(os.getcwd(), "artifacts")
OUT_DIR = os.path.join(os.getcwd(), "all_tasks")

LOGIN_URL = "https://web.mashov.info/students/login"
HOME_URL  = "https://web.mashov.info/students/main/home"

USER = os.getenv("MASHOV_USERNAME", "").strip()
PWD  = os.getenv("MASHOV_PASSWORD", "").strip()
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

def ensure_dirs():
    os.makedirs(ART_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

def save_debug(page, ts, prefix):
    try:
        page.screenshot(path=f"{ART_DIR}/{prefix}_{ts}.png", full_page=True)
        with open(f"{ART_DIR}/{prefix}_{ts}.html", "w", encoding="utf-8") as f:
            f.write(page.content())
    except Exception:
        pass

def wait_basic(page, ms=1500):
    try:
        page.wait_for_load_state("domcontentloaded", timeout=20000)
    except TimeoutError:
        pass
    page.wait_for_timeout(ms)


# ──────────────────────────────────────────────
#  תאריכים
# ──────────────────────────────────────────────
MONTHS_HE = {
    "ינואר": "01", "פברואר": "02", "מרץ": "03", "אפריל": "04",
    "מאי": "05", "יוני": "06", "יולי": "07", "אוגוסט": "08",
    "ספטמבר": "09", "אוקטובר": "10", "נובמבר": "11", "דצמבר": "12",
    "ינו": "01", "פבר": "02", "אפר": "04",
    "יונ": "06", "יול": "07", "אוג": "08", "ספט": "09", "אוק": "10",
    "נוב": "11", "דצמ": "12",
    "January": "01", "February": "02", "March": "03", "April": "04",
    "May": "05", "June": "06", "July": "07", "August": "08",
    "September": "09", "October": "10", "November": "11", "December": "12",
    "Jan": "01", "Feb": "02", "Mar": "03", "Apr": "04",
    "Jun": "06", "Jul": "07", "Aug": "08", "Sep": "09", "Oct": "10",
    "Nov": "11", "Dec": "12",
}

def parse_date(text):
    text = (text or "").strip()
    if not text:
        return None
    for p in [r'\d{1,2}/\d{1,2}/\d{2,4}', r'\d{1,2}\.\d{1,2}\.\d{2,4}', r'\d{4}-\d{2}-\d{2}']:
        m = re.search(p, text)
        if m:
            return m.group(0)
    m = re.search(r'(\d{1,2})\s+ב?([א-ת]{2,7}|[A-Za-z]{3,9})[׳\s,]+(\d{4})', text)
    if m:
        day, mon_str, year = m.group(1), m.group(2), m.group(3)
        for k, v in MONTHS_HE.items():
            if mon_str.startswith(k) or k.startswith(mon_str[:3]):
                return f"{int(day):02d}/{v}/{year}"
    m = re.search(r'(\d{1,2})\s+ב?([א-ת]{2,7}|[A-Za-z]{3,9})', text)
    if m:
        day, mon_str = m.group(1), m.group(2)
        for k, v in MONTHS_HE.items():
            if mon_str.startswith(k) or k.startswith(mon_str[:3]):
                return f"{int(day):02d}/{v}/{datetime.now().year}"
    return None

def days_until(date_str):
    if not date_str:
        return None
    for fmt in ["%d/%m/%Y", "%d/%m/%y", "%d.%m.%Y", "%d.%m.%y", "%Y-%m-%d"]:
        try:
            d = datetime.strptime(date_str, fmt)
            return (d - datetime.now()).days
        except Exception:
            continue
    return None


# ──────────────────────────────────────────────
#  Login
# ──────────────────────────────────────────────
def handle_reauth(page, ts):
    if page.locator('text="נא להזדהות מחדש"').count() == 0:
        return True
    print("[Moodle] Reauth popup detected")
    try:
        pw = page.locator('input[type="password"]:not([aria-hidden="true"])').first
        pw.wait_for(state="visible", timeout=8000)
        pw.click()
        pw.fill(PWD)
        page.get_by_role("button", name="כניסה").first.click()
        page.locator('text="נא להזדהות מחדש"').first.wait_for(state="detached", timeout=15000)
        print("[Moodle] Reauth OK")
        return True
    except Exception as e:
        print("[Moodle] Reauth failed:", e)
        save_debug(page, ts, "reauth_failed")
        return False

def login(page, ts):
    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_basic(page)

    if page.locator('text="נא להזדהות מחדש"').count() > 0:
        ok = handle_reauth(page, ts)
        page.goto(HOME_URL, wait_until="domcontentloaded")
        wait_basic(page)
        return ok

    if "login" not in page.url:
        print("[Moodle] Already logged in to Mashov")
        return True

    print("[Moodle] Logging in to Mashov...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    wait_basic(page)

    for u_sel, p_sel in [
        ('input[name="username"]', 'input[name="password"]'),
        ('input[type="text"]', 'input[type="password"]'),
    ]:
        try:
            page.wait_for_selector(u_sel, timeout=6000)
            page.fill(u_sel, USER)
            page.fill(p_sel, PWD)
            break
        except TimeoutError:
            continue

    try:
        page.locator('button[type="submit"]').first.click()
    except Exception:
        page.get_by_role("button", name="כניסה").click()

    wait_basic(page, 2000)
    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_basic(page)

    if page.locator('text="נא להזדהות מחדש"').count() > 0:
        return handle_reauth(page, ts)
    return "login" not in page.url


# ──────────────────────────────────────────────
#  Navigate to Moodle Assignments page
# ──────────────────────────────────────────────
def go_to_moodle_assignments(page, ts):
    """לוחץ על 'משימות Moodle' בתפריט הצדדי של Mashov"""
    print("[Moodle] Navigating to Moodle assignments page...")

    # נסה דרך התפריט הצדדי
    try:
        loc = page.locator('span[title="משימות Moodle"]')
        if loc.count() > 0:
            loc.first.click()
            page.wait_for_timeout(3000)
            if page.locator('mshv-moodle-assignments').count() > 0:
                print("[Moodle] ✅ Reached Moodle assignments page")
                return True
    except Exception:
        pass

    # fallback — כפתור מה-HOME splash
    try:
        loc = page.get_by_text("משימות Moodle", exact=True)
        if loc.count() > 0:
            loc.first.click()
            page.wait_for_timeout(3000)
            if page.locator('mshv-moodle-assignments').count() > 0:
                print("[Moodle] ✅ Reached Moodle assignments page")
                return True
    except Exception:
        pass

    # fallback — גלול וחפש בתפריט
    for _ in range(15):
        page.mouse.wheel(0, 1200)
        page.wait_for_timeout(400)
        try:
            loc = page.locator('span[title="משימות Moodle"]')
            if loc.count() > 0:
                loc.first.click()
                page.wait_for_timeout(3000)
                if page.locator('mshv-moodle-assignments').count() > 0:
                    return True
        except Exception:
            pass

    save_debug(page, ts, "moodle_assignments_nav_failed")
    return False


# ──────────────────────────────────────────────
#  Extract tasks from a tab
# ──────────────────────────────────────────────
def extract_tasks_from_tab(page, tab_index, tab_name, ts):
    """לוחץ על טאב ושולף את המשימות שבו"""
    tasks = []

    # לחץ על הטאב
    try:
        tab_selector = f'#mat-tab-group-0-label-{tab_index}'
        tab = page.locator(tab_selector)
        if tab.count() == 0:
            tab = page.locator('div[role="tab"]').nth(tab_index)
        tab.click()
        page.wait_for_timeout(2500)
    except Exception as e:
        print(f"  ❌ Could not click tab {tab_index} ({tab_name}): {e}")
        return tasks

    save_debug(page, ts, f"moodle_tab_{tab_index}_{tab_name}")

    # שלוף תוכן מהטאב הפעיל
    active = page.locator('.mat-mdc-tab-body-active')
    if active.count() == 0:
        print(f"  No active tab body found")
        return tasks

    # חפש items — Mashov משתמש ב-mat-list-item או divs
    items = active.locator('mat-list-item, .mat-mdc-list-item')
    count = items.count()

    if count > 0:
        print(f"  Found {count} list items")
        for i in range(count):
            task = parse_list_item(items.nth(i), tab_name)
            if task:
                tasks.append(task)
    else:
        # fallback — קרא את כל הטקסט ונסה לפרסר
        print(f"  No list items, parsing text...")
        tasks = parse_tab_text(active, tab_name)

    return tasks


def parse_list_item(item, tab_name):
    """מפרסר mat-list-item בודד למשימה"""
    try:
        text = item.inner_text().strip()
    except Exception:
        return None
    if not text or len(text) < 3:
        return None

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    task = {
        "source": "moodle",
        "title": "",
        "course": "",
        "url": "",
        "due_date": None,
        "days_left": None,
        "description": "",
    }

    # פרסר שורות — הדפוס הטיפוסי מה-screenshots:
    # שורה 1: "ספרות י9 - [217]" (קורס)
    # שורה 2: "שאלות חזרה לקראת הבחינה" (שם משימה)
    # שורה 3: "חדש להגשה עד: 17/12/2025 00:00" (תאריך)
    # שורה 4: "הגש" / "הצגה ב-Moodle" (כפתורים)

    skip_words = ["הגש", "הצגה ב", "Moodle", "הצגה"]

    meaningful_lines = []
    for line in lines:
        if any(sw in line for sw in skip_words):
            continue
        meaningful_lines.append(line)

    for line in meaningful_lines:
        # קורס עם [id]
        m = re.match(r'(.+?)\s*[\-–]\s*\[(\d+)\]$', line)
        if not m:
            m = re.match(r'(.+?)\s*\[(\d+)\]$', line)
        if m and not task["course"]:
            task["course"] = m.group(1).strip()
            task["course_id"] = m.group(2)
            continue

        # תאריך
        date = parse_date(line)
        if date and not task["due_date"]:
            task["due_date"] = date
            task["days_left"] = days_until(date)
            continue

        # ציון (מספר עשרוני שלילי כמו -1.00000)
        m_grade = re.match(r'^-?\d+\.\d+$', line)
        if m_grade:
            task["grade"] = line
            continue

        # שם משימה — השורה הראשונה שלא זיהינו
        if not task["title"] and len(line) > 2:
            task["title"] = line
        elif task["title"] and not task["description"] and len(line) > 2:
            task["description"] = line[:200]

    # חפש קישור ל-Moodle
    try:
        link = item.locator('a[href*="moodle"]')
        if link.count() > 0:
            task["url"] = link.first.get_attribute("href") or ""
    except Exception:
        pass

    # כפתור "הצגה ב-Moodle" — לפעמים זה כפתור ולא לינק
    if not task["url"]:
        try:
            btn = item.locator('button:has-text("Moodle"), a:has-text("Moodle")')
            if btn.count() > 0:
                href = btn.first.get_attribute("href") or ""
                if href:
                    task["url"] = href
        except Exception:
            pass

    if not task["title"]:
        return None
    return task


def parse_tab_text(active_body, tab_name):
    """fallback — פרסר מטקסט כשאין list items"""
    tasks = []
    try:
        text = active_body.inner_text().strip()
    except Exception:
        return tasks

    if not text or len(text) < 5:
        return tasks

    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # נסה לזהות בלוקים של משימות
    current = None
    skip_words = ["הגש", "הצגה ב", "Moodle", "הצגה", "מציג", "נבחרו"]

    for line in lines:
        if any(sw in line for sw in skip_words):
            continue

        # קורס [id]
        m = re.match(r'(.+?)\s*[\-–]?\s*\[(\d+)\]$', line)
        if m:
            if current and current.get("title"):
                tasks.append(current)
            current = {
                "source": "moodle",
                "title": "",
                "course": m.group(1).strip(),
                "course_id": m.group(2),
                "url": "",
                "due_date": None,
                "days_left": None,
                "description": "",
            }
            continue

        # תאריך
        date = parse_date(line)
        if date and current and not current.get("due_date"):
            current["due_date"] = date
            current["days_left"] = days_until(date)
            continue

        # שם משימה
        if current and not current.get("title") and len(line) > 2:
            current["title"] = line
        elif current and current.get("title") and not current.get("description") and len(line) > 2:
            current["description"] = line[:200]

    if current and current.get("title"):
        tasks.append(current)

    # חפש URLs
    try:
        links = active_body.locator('a[href*="moodle"]')
        for i in range(min(links.count(), len(tasks))):
            try:
                href = links.nth(i).get_attribute("href") or ""
                if href and i < len(tasks):
                    tasks[i]["url"] = href
            except Exception:
                pass
    except Exception:
        pass

    return tasks


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────
def main():
    if not USER or not PWD:
        print("[Moodle] Missing MASHOV credentials in .env")
        return []

    ensure_dirs()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        args = ["--disable-blink-features=AutomationControlled"]
        if HEADLESS:
            args += ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        else:
            args += ["--start-maximized"]

        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=HEADLESS,
            args=args,
            viewport={"width": 1600, "height": 900},
        )
        page = context.new_page()

        # 1) התחברות ל-Mashov
        if not login(page, ts):
            print("[Moodle] Mashov login failed")
            save_debug(page, ts, "mashov_login_failed")
            context.close()
            return []

        # 2) נווט לדף "משימות Moodle" בתוך Mashov
        if not go_to_moodle_assignments(page, ts):
            print("[Moodle] Could not reach Moodle assignments page")
            context.close()
            return []

        save_debug(page, ts, "moodle_assignments_page")

        # 3) קרא מכל 3 הטאבים
        TABS = {
            0: "להגשה",
            1: "הושלמו",
            2: "באיחור",
        }

        all_tasks = []
        for tab_idx, tab_name in TABS.items():
            print(f"\n[Moodle] === Tab: {tab_name} (index {tab_idx}) ===")
            tasks = extract_tasks_from_tab(page, tab_idx, tab_name, ts)
            print(f"  → {len(tasks)} tasks")
            for t in tasks:
                print(f"    📝 [{t.get('course','')}] {t.get('title','')} | {t.get('due_date','no date')}")
            all_tasks.extend(tasks)

        # 4) סנן — שמור רק "להגשה" ו"באיחור"
        # (שומרים גם "הושלמו" ב-JSON אבל מסמנים אותם, כדי שב-dashboard נוכל להציג הכל)
        for t in all_tasks:
            t.pop("status", None)

        pending = [t for t in all_tasks]  # שומרים הכל — הסינון יהיה ב-run_all / WhatsApp

        print(f"\n[Moodle] Summary: {len(pending)} total tasks from all tabs")

        # 5) שמור
        out_path = os.path.join(OUT_DIR, f"moodle_tasks_{ts}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(pending, f, ensure_ascii=False, indent=2)

        print(f"[Moodle] ✅ Saved → {out_path}")
        context.close()
        return pending

if __name__ == "__main__":
    main()
