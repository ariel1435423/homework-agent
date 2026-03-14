from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")

LOGIN_URL = "https://web.mashov.info/students/login"
HOME_URL  = "https://web.mashov.info/students/main/home"  # ← זה העמוד הנכון אצלך

USER = os.getenv("MASHOV_USERNAME", "").strip()
PWD  = os.getenv("MASHOV_PASSWORD", "").strip()

def save_debug(page, ts, prefix):
    os.makedirs("artifacts", exist_ok=True)
    page.screenshot(path=f"artifacts/{prefix}_{ts}.png", full_page=True)
    with open(f"artifacts/{prefix}_{ts}.html", "w", encoding="utf-8") as f:
        f.write(page.content())

def wait_basic(page, ms=1500):
    try:
        page.wait_for_load_state("domcontentloaded", timeout=20000)
    except TimeoutError:
        pass
    page.wait_for_timeout(ms)

def handle_reauth_popup(page, ts) -> bool:
    # פופאפ "נא להזדהות מחדש"
    if page.locator('text="נא להזדהות מחדש"').count() == 0:
        return False

    # למלא סיסמה
    password_selectors = [
        'input[placeholder*="סיסמה"]',
        'input[type="password"]',
        'input[autocomplete="current-password"]',
    ]
    filled = False
    for sel in password_selectors:
        try:
            if page.locator(sel).count() > 0:
                page.locator(sel).first.fill(PWD)
                filled = True
                break
        except Exception:
            continue

    if not filled:
        save_debug(page, ts, "reauth_password_field_not_found")
        return False

    # ללחוץ "כניסה"
    clicked = False
    try:
        btn = page.get_by_role("button", name="כניסה")
        if btn.count() > 0:
            btn.first.click()
            clicked = True
    except Exception:
        pass

    if not clicked:
        try:
            loc = page.locator('text="כניסה"')
            if loc.count() > 0:
                loc.first.click()
                clicked = True
        except Exception:
            pass

    if not clicked:
        save_debug(page, ts, "reauth_login_button_not_found")
        return False

    # לחכות שהפופאפ ייעלם
    try:
        page.wait_for_selector('text="נא להזדהות מחדש"', state="detached", timeout=20000)
    except TimeoutError:
        save_debug(page, ts, "reauth_popup_did_not_close")
        return False

    return True

def is_on_login_page(page) -> bool:
    return "login" in page.url

def login_if_needed(page, ts) -> bool:
    # ננסה לגשת ל-HOME. אם לא מחובר ניזרק ל-login.
    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_basic(page)

    # טיפול בפופאפ reauth אם קיים
    if page.locator('text="נא להזדהות מחדש"').count() > 0:
        ok = handle_reauth_popup(page, ts)
        wait_basic(page)
        return ok

    if not is_on_login_page(page):
        # כנראה מחובר
        return True

    # להתחבר עם user+pass
    page.goto(LOGIN_URL, wait_until="domcontentloaded")
    wait_basic(page)

    save_debug(page, ts, "mashov_login_page")

    selectors = [
        ('input[name="username"]', 'input[name="password"]'),
        ('input[autocomplete="username"]', 'input[autocomplete="current-password"]'),
        ('input[type="text"]', 'input[type="password"]'),
    ]

    filled = False
    for u_sel, p_sel in selectors:
        try:
            page.wait_for_selector(u_sel, timeout=8000)
            page.wait_for_selector(p_sel, timeout=8000)
            page.fill(u_sel, USER)
            page.fill(p_sel, PWD)
            filled = True
            break
        except TimeoutError:
            continue

    if not filled:
        save_debug(page, ts, "login_fields_not_found")
        return False

    # submit
    clicked = False
    try:
        page.locator('button[type="submit"]').first.click(timeout=2000)
        clicked = True
    except Exception:
        pass

    if not clicked:
        for name in ["כניסה", "התחבר", "Login", "Sign in"]:
            try:
                b = page.get_by_role("button", name=name)
                if b.count() > 0:
                    b.first.click()
                    clicked = True
                    break
            except Exception:
                pass

    if not clicked:
        save_debug(page, ts, "login_button_not_found")
        return False

    # אחרי login: ללכת ל-HOME (העמוד שמציג את כפתור Moodle)
    page.goto(HOME_URL, wait_until="domcontentloaded")
    wait_basic(page, 2500)

    # אם קפץ reauth ישר אחרי login
    if page.locator('text="נא להזדהות מחדש"').count() > 0:
        return handle_reauth_popup(page, ts)

    save_debug(page, ts, "mashov_home_after_login")
    return True

def click_moodle_on_home(page, ts) -> bool:
    # בעמוד home אצלך רואים את הכפתור "כניסה ל-Moodle" (לפעמים צריך לגלול בתפריט)
    target_texts = ["כניסה ל-Moodle", "Moodle משימות", "משימות Moodle", "Moodle", "מודל"]

    # נסה למצוא וללחוץ בלי גלילה
    for t in target_texts:
        loc = page.locator(f'text="{t}"')
        if loc.count() > 0:
            try:
                loc.first.scroll_into_view_if_needed()
            except Exception:
                pass
            loc.first.click()
            return True

    # אם לא נמצא, נגלול את העמוד כמה פעמים ונחפש שוב
    for _ in range(10):
        page.mouse.wheel(0, 1400)
        page.wait_for_timeout(600)
        for t in target_texts:
            loc = page.locator(f'text="{t}"')
            if loc.count() > 0:
                try:
                    loc.first.scroll_into_view_if_needed()
                except Exception:
                    pass
                loc.first.click()
                return True

    save_debug(page, ts, "moodle_button_not_found_on_home")
    return False

def is_moodle_guest(page) -> bool:
    try:
        txt = (page.inner_text("body") or "").lower()
    except Exception:
        txt = ""
    return ("guest" in txt) or ("אורח" in txt)

def main():
    if not USER or not PWD:
        print("Missing MASHOV_USERNAME or MASHOV_PASSWORD in .env")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            viewport={"width": 1600, "height": 900},
        )

        page = context.new_page()

        # 1) התחברות + להגיע ל-HOME
        ok = login_if_needed(page, ts)
        if not ok:
            save_debug(page, ts, "mashov_login_failed")
            print("❌ Mashov login failed. Check artifacts/mashov_login_failed_*")
            context.close()
            return

        # 2) לוודא שאנחנו ב-HOME
        page.goto(HOME_URL, wait_until="domcontentloaded")
        wait_basic(page, 2500)
        save_debug(page, ts, "mashov_home_ready")

        # 3) קליק על Moodle מתוך HOME
        clicked = click_moodle_on_home(page, ts)
        if not clicked:
            print("⚠️ Could not find Moodle button on HOME. Check artifacts/moodle_button_not_found_on_home_*")
            context.close()
            return

        # 4) לחכות למעבר ל-moodle
        target = page
        try:
            target.wait_for_url("**moodle.mashov.info**", timeout=45000)
        except TimeoutError:
            if len(context.pages) > 1:
                target = context.pages[-1]
            try:
                target.wait_for_url("**moodle.mashov.info**", timeout=45000)
            except TimeoutError:
                save_debug(target, ts, "mashov_moodle_nav_fail")
                print("❌ Clicked Moodle but did not reach moodle.mashov.info")
                context.close()
                return

        try:
            target.wait_for_load_state("domcontentloaded", timeout=20000)
        except TimeoutError:
            pass
        target.wait_for_timeout(3000)

        save_debug(target, ts, "moodle_after_sso")

        if is_moodle_guest(target):
            print("⚠️ Reached Moodle but looks like Guest. Check artifacts/moodle_after_sso_*.png")
        else:
            print("✅ SUCCESS: Reached Moodle via Mashov SSO (not Guest).")

        context.close()

if __name__ == "__main__":
    main()