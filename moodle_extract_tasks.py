# moodle_extract_tasks.py — v3
# גרסה מפושטת: קורא משימות ישירות מדף "משימות Moodle" של Mashov
# בלי SSO ל-Moodle! הרבה יותר מהיר ופשוט.
from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
from datetime import datetime
import glob, os, json, re, sys, time

load_dotenv()

for stream_name in ["stdout", "stderr"]:
    try:
        getattr(sys, stream_name).reconfigure(encoding="utf-8")
    except Exception:
        pass

PROFILE_DIR = os.getenv("MOODLE_PROFILE_DIR", os.path.join(os.getcwd(), "moodle_profile"))
ART_DIR = os.path.join(os.getcwd(), "artifacts")
OUT_DIR = os.path.join(os.getcwd(), "all_tasks")
STUDENT_UUID_CACHE = os.path.join(ART_DIR, "mashov_student_uuid.txt")
SCHOOL_CODE_CACHE = os.path.join(ART_DIR, "mashov_school_code.txt")

LOGIN_URL = "https://web.mashov.info/students/login"
HOME_URL = "https://web.mashov.info/students/main/home"

USER = os.getenv("MASHOV_USERNAME", "").strip()
PWD = os.getenv("MASHOV_PASSWORD", "").strip()
SCHOOL_CODE = os.getenv("MASHOV_SCHOOL_CODE", "").strip()
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
MANUAL_LOGIN_TIMEOUT_MS = max(60000, int(os.getenv("MASHOV_MANUAL_LOGIN_TIMEOUT_MS", "300000")))
MANUAL_LOGIN_ENABLED = os.getenv("MASHOV_MANUAL_LOGIN", "false").lower() == "true" and not HEADLESS


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


def is_mashov_loading(page):
    try:
        loader = page.locator("mshv-loader.loading")
        return loader.count() > 0 and loader.first.is_visible()
    except Exception:
        return False


def has_student_context(page):
    try:
        if page.locator('img[src*="/api/user/"]').count() > 0:
            return True
    except Exception:
        pass

    for selector in [
        'button[aria-label="בחירת תלמיד לצפייה"] .mdc-button__label',
        "mshv-student-block .mdc-button__label",
        ".mshv-toolbar-info span",
    ]:
        try:
            loc = page.locator(selector)
            if loc.count() == 0:
                continue
            for i in range(min(loc.count(), 4)):
                text = (loc.nth(i).inner_text() or "").strip()
                if text and text not in ["כל השנה", "תשפ\"ו - 2026", "תשפ״ו - 2026"]:
                    return True
        except Exception:
            continue

    return False


def wait_for_student_context(page, timeout_ms=20000):
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        if has_student_context(page) and not is_mashov_loading(page):
            code = get_school_code(page)
            if code:
                cache_school_code(code)
            student_uuid = get_student_uuid(page)
            if student_uuid:
                cache_student_uuid(student_uuid)
            return True
        page.wait_for_timeout(500)
    return has_student_context(page)


def wait_for_manual_login(page, ts, timeout_ms=MANUAL_LOGIN_TIMEOUT_MS):
    if not MANUAL_LOGIN_ENABLED:
        return False

    print("[Moodle] Waiting for manual Mashov login in the opened browser...")
    deadline = time.time() + (timeout_ms / 1000)

    while time.time() < deadline:
        try:
            if is_on_moodle_assignments_page(page):
                wait_for_student_context(page, 10000)
                return True

            if "login" not in page.url and wait_for_student_context(page, 3000):
                return True
        except Exception:
            pass

        page.wait_for_timeout(1000)

    save_debug(page, ts, "mashov_manual_login_timeout")
    return False


def prompt_manual_login(page, ts):
    if not MANUAL_LOGIN_ENABLED:
        return False

    try:
        if has_mashov_error_dialog(page):
            for selector in ['button:has-text("הבנתי")', "mat-snack-bar-container button"]:
                try:
                    loc = page.locator(selector)
                    if loc.count() > 0:
                        loc.first.click()
                        page.wait_for_timeout(500)
                except Exception:
                    pass

            logout = page.locator('button:has-text("התנתק/י")')
            if logout.count() > 0:
                logout.first.click()
                page.wait_for_timeout(1500)
    except Exception:
        pass

    try:
        if "login" not in page.url and not is_on_moodle_assignments_page(page):
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
            wait_basic(page, 1000)
    except Exception:
        pass

    return wait_for_manual_login(page, ts)


UUID_RE = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"


def extract_student_uuid_from_text(text):
    if not text:
        return None

    for pattern in [
        rf"/students/main/students/({UUID_RE})/",
        rf"/api/user/({UUID_RE})/",
        rf"\b({UUID_RE})\b",
    ]:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).lower()
    return None


def extract_school_code_from_text(text):
    if not text:
        return None

    for pattern in [
        r"semel=(\d{5,7})",
        r"\b(\d{5,7})\b",
    ]:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def cache_student_uuid(student_uuid):
    if not student_uuid:
        return
    try:
        ensure_dirs()
        with open(STUDENT_UUID_CACHE, "w", encoding="utf-8") as f:
            f.write(student_uuid)
    except Exception:
        pass


def cache_school_code(code):
    if not code:
        return
    try:
        ensure_dirs()
        with open(SCHOOL_CODE_CACHE, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception:
        pass


def load_cached_student_uuid():
    try:
        if os.path.exists(STUDENT_UUID_CACHE):
            with open(STUDENT_UUID_CACHE, "r", encoding="utf-8") as f:
                student_uuid = extract_student_uuid_from_text(f.read().strip())
                if student_uuid:
                    return student_uuid
    except Exception:
        pass

    patterns = [
        os.path.join(ART_DIR, "moodle_*.html"),
        os.path.join(ART_DIR, "mashov_*.html"),
        os.path.join(ART_DIR, "reauth_*.html"),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    for path in sorted(candidates, key=os.path.getmtime, reverse=True)[:15]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                student_uuid = extract_student_uuid_from_text(f.read())
                if student_uuid:
                    cache_student_uuid(student_uuid)
                    return student_uuid
        except Exception:
            continue

    return None


def load_cached_school_code():
    if SCHOOL_CODE:
        return SCHOOL_CODE

    try:
        if os.path.exists(SCHOOL_CODE_CACHE):
            with open(SCHOOL_CODE_CACHE, "r", encoding="utf-8") as f:
                code = extract_school_code_from_text(f.read().strip())
                if code:
                    return code
    except Exception:
        pass

    patterns = [
        os.path.join(ART_DIR, "moodle_*.html"),
        os.path.join(ART_DIR, "mashov_*.html"),
        os.path.join(ART_DIR, "reauth_*.html"),
    ]
    candidates = []
    for pattern in patterns:
        candidates.extend(glob.glob(pattern))

    for path in sorted(candidates, key=os.path.getmtime, reverse=True)[:15]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                code = extract_school_code_from_text(f.read())
                if code:
                    cache_school_code(code)
                    return code
        except Exception:
            continue

    return None


def get_student_uuid(page):
    sources = []

    try:
        sources.append(page.url)
    except Exception:
        pass

    for selector in [
        'img[src*="/api/user/"]',
        'a[href*="/students/main/students/"]',
    ]:
        try:
            loc = page.locator(selector)
            if loc.count() > 0:
                value = loc.first.get_attribute("src") or loc.first.get_attribute("href")
                if value:
                    sources.append(value)
        except Exception:
            pass

    try:
        sources.append(page.content())
    except Exception:
        pass

    try:
        storage_dump = page.evaluate(
            """() => {
                const values = [];
                for (const store of [window.localStorage, window.sessionStorage]) {
                    if (!store) continue;
                    for (let i = 0; i < store.length; i++) {
                        const key = store.key(i);
                        values.push(key || "");
                        values.push(store.getItem(key) || "");
                    }
                }
                return values.join("\\n");
            }"""
        )
        if storage_dump:
            sources.append(storage_dump)
    except Exception:
        pass

    for source in sources:
        student_uuid = extract_student_uuid_from_text(source)
        if student_uuid:
            cache_student_uuid(student_uuid)
            return student_uuid

    return load_cached_student_uuid()


def get_school_code(page):
    if SCHOOL_CODE:
        return SCHOOL_CODE

    sources = []

    try:
        sources.append(page.url)
    except Exception:
        pass

    try:
        sources.append(page.content())
    except Exception:
        pass

    try:
        storage_dump = page.evaluate(
            """() => {
                const values = [];
                for (const store of [window.localStorage, window.sessionStorage]) {
                    if (!store) continue;
                    for (let i = 0; i < store.length; i++) {
                        const key = store.key(i);
                        values.push(key || "");
                        values.push(store.getItem(key) || "");
                    }
                }
                return values.join("\\n");
            }"""
        )
        if storage_dump:
            sources.append(storage_dump)
    except Exception:
        pass

    for source in sources:
        code = extract_school_code_from_text(source)
        if code:
            cache_school_code(code)
            return code

    return load_cached_school_code()


def ensure_school_selected(page, ts):
    enabled_user = page.locator(
        '#usernameInput:not([disabled]), input[name="username"]:not([disabled]), input[placeholder*="שם משתמש"]:not([disabled])'
    )
    if enabled_user.count() > 0:
        return True

    school_input = page.locator('#schoolSelector, input[aria-label="ביה\\"ס"], input[placeholder="ביה\\"ס"]').first
    if school_input.count() == 0:
        return True

    school_code = get_school_code(page)
    if not school_code:
        print("[Moodle] Missing school code for Mashov login")
        save_debug(page, ts, "mashov_school_code_missing")
        return False

    try:
        school_input.click()
        school_input.fill("")
        school_input.press_sequentially(school_code)
        page.wait_for_timeout(1200)

        options = page.locator('[role="option"]')
        if options.count() > 0:
            options.first.click()
        else:
            school_input.press("ArrowDown")
            page.wait_for_timeout(250)
            school_input.press("Enter")

        page.wait_for_timeout(1500)
    except Exception as exc:
        print("[Moodle] School selection failed:", exc)
        save_debug(page, ts, "mashov_school_select_failed")
        return False

    if enabled_user.count() > 0:
        cache_school_code(school_code)
        return True

    save_debug(page, ts, "mashov_school_select_failed")
    return False


def open_direct_moodle_assignments(page, ts):
    student_uuid = get_student_uuid(page)
    if not student_uuid:
        return False

    url = f"https://web.mashov.info/students/main/students/{student_uuid}/moodleAssignments"
    print(f"[Moodle] Trying direct Moodle assignments route for student {student_uuid}")

    try:
        page.goto(url, wait_until="domcontentloaded")
        wait_basic(page, 1500)
        wait_for_student_context(page, 20000)
        if wait_for_moodle_assignments(page):
            cache_student_uuid(student_uuid)
            return True
    except Exception:
        pass

    save_debug(page, ts, "moodle_direct_route_failed")
    return False


def is_on_moodle_assignments_page(page):
    try:
        if page.locator("mshv-moodle-assignments").count() > 0:
            return True
    except Exception:
        pass

    try:
        has_title = page.locator('text="משימות Moodle"').count() > 0
        has_tabs = page.locator("mat-tab-group").count() > 0
        if has_title and has_tabs:
            return True
    except Exception:
        pass

    try:
        tab_count = page.locator('div[role="tab"]').count()
        if tab_count >= 3 and page.locator('text="משימות שהושלמו"').count() > 0:
            return True
    except Exception:
        pass

    return False


def wait_for_moodle_assignments(page, timeout_ms=12000):
    deadline = time.time() + (timeout_ms / 1000)
    while time.time() < deadline:
        if is_on_moodle_assignments_page(page):
            return True
        page.wait_for_timeout(250)
    return is_on_moodle_assignments_page(page)


def has_mashov_error_dialog(page):
    try:
        if page.locator("mshv-lock-dialog").count() > 0:
            return True
    except Exception:
        pass

    for text in [
        'text="אירעה שגיאה, עליך להתנתק."',
        'text="אירעה שגיאה בהבאת המידע"',
        'text="על-מנת לשחרר את המסך יש להזין סיסמה"',
    ]:
        try:
            if page.locator(text).count() > 0:
                return True
        except Exception:
            pass

    return False


def has_password_popup(page):
    for text in [
        'text="נא להזדהות מחדש"',
        'text="על-מנת לשחרר את המסך יש להזין סיסמה"',
    ]:
        try:
            if page.locator(text).count() > 0:
                return True
        except Exception:
            pass

    try:
        dialog_password = page.locator('mat-dialog-container input[type="password"]:not([aria-hidden="true"])')
        if dialog_password.count() > 0:
            return True
    except Exception:
        pass

    return False


def recover_from_mashov_error(page, ts):
    if not has_mashov_error_dialog(page):
        return False

    print("[Moodle] Mashov error/lock dialog detected, forcing re-login")
    save_debug(page, ts, "mashov_error_dialog")

    for selector in ['button:has-text("הבנתי")', "mat-snack-bar-container button"]:
        try:
            loc = page.locator(selector)
            if loc.count() > 0:
                loc.first.click()
                page.wait_for_timeout(1000)
        except Exception:
            pass

    try:
        logout = page.locator('button:has-text("התנתק/י")')
        if logout.count() > 0:
            logout.first.click()
            page.wait_for_timeout(1500)
    except Exception:
        pass

    try:
        page.wait_for_url("**/students/login", timeout=15000)
    except Exception:
        try:
            page.goto(LOGIN_URL, wait_until="domcontentloaded")
        except Exception:
            pass

    wait_basic(page, 1500)
    return True


# ──────────────────────────────────────────────
#  תאריכים
# ──────────────────────────────────────────────
MONTHS_HE = {
    "ינואר": "01",
    "פברואר": "02",
    "מרץ": "03",
    "אפריל": "04",
    "מאי": "05",
    "יוני": "06",
    "יולי": "07",
    "אוגוסט": "08",
    "ספטמבר": "09",
    "אוקטובר": "10",
    "נובמבר": "11",
    "דצמבר": "12",
    "ינו": "01",
    "פבר": "02",
    "אפר": "04",
    "יונ": "06",
    "יול": "07",
    "אוג": "08",
    "ספט": "09",
    "אוק": "10",
    "נוב": "11",
    "דצמ": "12",
    "January": "01",
    "February": "02",
    "March": "03",
    "April": "04",
    "May": "05",
    "June": "06",
    "July": "07",
    "August": "08",
    "September": "09",
    "October": "10",
    "November": "11",
    "December": "12",
    "Jan": "01",
    "Feb": "02",
    "Mar": "03",
    "Apr": "04",
    "Jun": "06",
    "Jul": "07",
    "Aug": "08",
    "Sep": "09",
    "Oct": "10",
    "Nov": "11",
    "Dec": "12",
}


def parse_date(text):
    text = (text or "").strip()
    if not text:
        return None
    for p in [r"\d{1,2}/\d{1,2}/\d{2,4}", r"\d{1,2}\.\d{1,2}\.\d{2,4}", r"\d{4}-\d{2}-\d{2}"]:
        m = re.search(p, text)
        if m:
            return m.group(0)
    m = re.search(r"(\d{1,2})\s+ב?([א-ת]{2,7}|[A-Za-z]{3,9})[׳\s,]+(\d{4})", text)
    if m:
        day, mon_str, year = m.group(1), m.group(2), m.group(3)
        for k, v in MONTHS_HE.items():
            if mon_str.startswith(k) or k.startswith(mon_str[:3]):
                return f"{int(day):02d}/{v}/{year}"
    m = re.search(r"(\d{1,2})\s+ב?([א-ת]{2,7}|[A-Za-z]{3,9})", text)
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
    if not has_password_popup(page):
        return True
    print("[Moodle] Password popup detected")
    try:
        pw = page.locator('mat-dialog-container input[type="password"]:not([aria-hidden="true"]), input[type="password"]:not([aria-hidden="true"])').first
        pw.wait_for(state="visible", timeout=8000)
        pw.click()
        pw.fill(PWD)
        for selector in [
            'mat-dialog-container button:has-text("כניסה")',
            'button:has-text("כניסה")',
            'button:has-text("אישור")',
            'button:has-text("המשך")',
        ]:
            button = page.locator(selector)
            if button.count() > 0:
                button.first.click()
                break

        page.wait_for_timeout(1500)
        print("[Moodle] Password popup handled")
        return True
    except Exception as e:
        print("[Moodle] Password popup handling failed:", e)
        save_debug(page, ts, "reauth_failed")
        return False


def login(page, ts):
    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_basic(page)

    if has_password_popup(page):
        ok = handle_reauth(page, ts)
        if ok:
            page.goto(HOME_URL, wait_until="domcontentloaded")
            wait_basic(page)
            wait_for_student_context(page, 20000)
            return True

    if has_mashov_error_dialog(page):
        if prompt_manual_login(page, ts):
            return True
        recover_from_mashov_error(page, ts)

    if has_password_popup(page):
        ok = handle_reauth(page, ts)
        page.goto(HOME_URL, wait_until="domcontentloaded")
        wait_basic(page)
        if ok:
            wait_for_student_context(page, 20000)
        return ok

    if "login" not in page.url:
        wait_for_student_context(page, 20000)
        print("[Moodle] Already logged in to Mashov")
        return True

    print("[Moodle] Logging in to Mashov...")
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    wait_basic(page)

    if not ensure_school_selected(page, ts):
        print("[Moodle] Could not select school on login page")
        return False

    filled = False
    for u_sel, p_sel in [
        ("#usernameInput", "#passwordInput"),
        ('input[name="username"]', 'input[name="password"]'),
        ('input[type="text"]', 'input[type="password"]'),
    ]:
        try:
            page.wait_for_selector(f"{u_sel}:not([disabled])", timeout=6000)
            page.locator(u_sel).first.click()
            page.fill(u_sel, USER)
            page.locator(p_sel).first.click()
            page.fill(p_sel, PWD)
            filled = True
            break
        except TimeoutError:
            continue

    if not filled:
        print("[Moodle] Login form not found")
        save_debug(page, ts, "mashov_login_form_missing")
        if prompt_manual_login(page, ts):
            return True
        return False

    page.wait_for_timeout(500)

    submitted = False
    for selector in [
        'button#submitButton:not([disabled])',
        'button[type="submit"]:not([disabled])',
        'button:has-text("כניסה"):not([disabled])',
    ]:
        try:
            button = page.locator(selector)
            if button.count() > 0:
                button.first.click()
                submitted = True
                break
        except Exception:
            pass

    if not submitted:
        try:
            page.locator('input[name="password"], input[type="password"]').first.press("Enter")
            submitted = True
        except Exception:
            pass

    if not submitted:
        print("[Moodle] Could not submit login form")
        save_debug(page, ts, "mashov_login_submit_failed")
        if prompt_manual_login(page, ts):
            return True
        return False

    wait_basic(page, 2000)
    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_basic(page)
    wait_for_student_context(page, 20000)

    if has_password_popup(page):
        return handle_reauth(page, ts)
    if "login" not in page.url:
        return True
    return prompt_manual_login(page, ts)


# ──────────────────────────────────────────────
#  Navigate to Moodle Assignments page
# ──────────────────────────────────────────────
def go_to_moodle_assignments(page, ts):
    """לוחץ על 'משימות Moodle' בתפריט הצדדי של Mashov"""
    print("[Moodle] Navigating to Moodle assignments page...")

    for attempt in range(3):
        if has_password_popup(page):
            ok = handle_reauth(page, ts)
            if not ok:
                return False
            try:
                page.goto(HOME_URL, wait_until="domcontentloaded")
                wait_basic(page)
            except Exception:
                pass

        if wait_for_moodle_assignments(page, 1500):
            wait_for_student_context(page, 15000)
            cache_student_uuid(get_student_uuid(page))
            print("[Moodle] Already on Moodle assignments page")
            return True

        if open_direct_moodle_assignments(page, ts):
            print("[Moodle] ✅ Reached Moodle assignments page via direct route")
            return True

        if has_mashov_error_dialog(page):
            recover_from_mashov_error(page, ts)
            if has_password_popup(page):
                ok = handle_reauth(page, ts)
                if not ok:
                    return False
            if wait_for_moodle_assignments(page, 1500):
                wait_for_student_context(page, 15000)
                cache_student_uuid(get_student_uuid(page))
                print("[Moodle] ✅ Reached Moodle assignments page")
                return True
            if open_direct_moodle_assignments(page, ts):
                print("[Moodle] ✅ Reached Moodle assignments page via direct route")
                return True
            try:
                page.goto(HOME_URL, wait_until="domcontentloaded")
                wait_basic(page)
            except Exception:
                pass

        try:
            loc = page.locator('button:has(span[title="משימות Moodle"]), span[title="משימות Moodle"]')
            if loc.count() > 0:
                loc.first.scroll_into_view_if_needed()
                loc.first.click()
                if wait_for_moodle_assignments(page):
                    wait_for_student_context(page, 15000)
                    cache_student_uuid(get_student_uuid(page))
                    print("[Moodle] ✅ Reached Moodle assignments page")
                    return True
        except Exception:
            pass

        try:
            loc = page.get_by_text("משימות Moodle", exact=True)
            if loc.count() > 0:
                loc.first.scroll_into_view_if_needed()
                loc.first.click()
                if wait_for_moodle_assignments(page):
                    wait_for_student_context(page, 15000)
                    cache_student_uuid(get_student_uuid(page))
                    print("[Moodle] ✅ Reached Moodle assignments page")
                    return True
        except Exception:
            pass

        try:
            loc = page.get_by_role("button", name="משימות Moodle")
            if loc.count() > 0:
                loc.first.scroll_into_view_if_needed()
                loc.first.click()
                if wait_for_moodle_assignments(page):
                    wait_for_student_context(page, 15000)
                    cache_student_uuid(get_student_uuid(page))
                    print("[Moodle] ✅ Reached Moodle assignments page")
                    return True
        except Exception:
            pass

        for _ in range(15):
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(400)
            if is_on_moodle_assignments_page(page):
                wait_for_student_context(page, 15000)
                cache_student_uuid(get_student_uuid(page))
                print("[Moodle] ✅ Reached Moodle assignments page")
                return True
            if has_password_popup(page):
                ok = handle_reauth(page, ts)
                if not ok:
                    return False
            try:
                loc = page.locator('button:has(span[title="משימות Moodle"]), span[title="משימות Moodle"]')
                if loc.count() > 0:
                    loc.first.scroll_into_view_if_needed()
                    loc.first.click()
                    if wait_for_moodle_assignments(page):
                        wait_for_student_context(page, 15000)
                        cache_student_uuid(get_student_uuid(page))
                        print("[Moodle] ✅ Reached Moodle assignments page")
                        return True
            except Exception:
                pass

        if open_direct_moodle_assignments(page, ts):
            print("[Moodle] ✅ Reached Moodle assignments page via direct route")
            return True

        if has_mashov_error_dialog(page) and attempt < 2:
            recover_from_mashov_error(page, ts)
            continue

        if is_on_moodle_assignments_page(page):
            wait_for_student_context(page, 15000)
            cache_student_uuid(get_student_uuid(page))
            print("[Moodle] ✅ Reached Moodle assignments page")
            return True

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
        tab_selector = f"#mat-tab-group-0-label-{tab_index}"
        tab = page.locator(tab_selector)
        if tab.count() == 0:
            tab = page.locator('div[role="tab"]').nth(tab_index)
        else:
            tab = tab.first

        is_selected = (tab.get_attribute("aria-selected") or "").lower() == "true"
        if not is_selected:
            try:
                tab.scroll_into_view_if_needed()
                tab.click(timeout=5000)
            except Exception:
                tab.evaluate("(el) => el.click()")
            page.wait_for_timeout(1500)
    except Exception as e:
        print(f"  ❌ Could not click tab {tab_index} ({tab_name}): {e}")
        return tasks

    save_debug(page, ts, f"moodle_tab_{tab_index}_{tab_name}")

    # שלוף תוכן מהטאב הפעיל
    active = page.locator(".mat-mdc-tab-body-active")
    if active.count() == 0:
        active = page.locator(f"#mat-tab-group-0-content-{tab_index}")
        if active.count() == 0:
            print("  No active tab body found")
            return tasks

    # חפש items — Mashov משתמש ב-mat-list-item או divs
    items = active.locator("mat-list-item, .mat-mdc-list-item")
    count = items.count()

    if count > 0:
        print(f"  Found {count} list items")
        for i in range(count):
            task = parse_list_item(items.nth(i), tab_name)
            if task:
                tasks.append(task)
    else:
        # fallback — קרא את כל הטקסט ונסה לפרסר
        print("  No list items, parsing text...")
        tasks = parse_tab_text(active, tab_name)

    status_map = {
        "להגשה": "active",
        "הושלמו": "completed",
        "באיחור": "late",
    }
    for task in tasks:
        task["status"] = status_map.get(tab_name, task.get("status", "active"))

    return tasks


def parse_list_item(item, tab_name):
    """מפרסר mat-list-item בודד למשימה"""
    try:
        text = item.inner_text().strip()
    except Exception:
        return None
    if not text or len(text) < 3:
        return None

    lines = [l.strip() for l in text.split("\n") if l.strip()]

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
        m = re.match(r"(.+?)\s*[\-–]\s*\[(\d+)\]$", line)
        if not m:
            m = re.match(r"(.+?)\s*\[(\d+)\]$", line)
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
        m_grade = re.match(r"^-?\d+\.\d+$", line)
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

    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # נסה לזהות בלוקים של משימות
    current = None
    skip_words = ["הגש", "הצגה ב", "Moodle", "הצגה", "מציג", "נבחרו"]

    for line in lines:
        if any(sw in line for sw in skip_words):
            continue

        # קורס [id]
        m = re.match(r"(.+?)\s*[\-–]?\s*\[(\d+)\]$", line)
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
                print(f"    📝 [{t.get('course', '')}] {t.get('title', '')} | {t.get('due_date', 'no date')}")
            all_tasks.extend(tasks)

        pending = [t for t in all_tasks]

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
