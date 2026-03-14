from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")
LOGIN_URL = "https://web.mashov.info/students/login"
DASH_URL = "https://web.mashov.info/students/main/dashboard"

USER = os.getenv("MASHOV_USERNAME", "").strip()
PWD = os.getenv("MASHOV_PASSWORD", "").strip()

def save_debug(page, ts, prefix):
    os.makedirs("artifacts", exist_ok=True)
    page.screenshot(path=f"artifacts/{prefix}_{ts}.png", full_page=True)
    with open(f"artifacts/{prefix}_{ts}.html", "w", encoding="utf-8") as f:
        f.write(page.content())

def is_logged_in(page) -> bool:
    # אם הצלחנו להגיע לדשבורד ולא נתקענו בלוגין
    return ("dashboard" in page.url) and ("login" not in page.url)

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

        # 1) נסה קודם דשבורד (אולי כבר מחובר)
        page.goto(DASH_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except TimeoutError:
            pass

        if is_logged_in(page):
            save_debug(page, ts, "mashov_already_logged_in")
            print("✅ Already logged in (session active).")
            context.close()
            return

        # 2) אם לא מחובר -> לדף login
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=25000)
        except TimeoutError:
            pass

        save_debug(page, ts, "mashov_login_page")

        # 3) למלא שם משתמש + סיסמה
        # אנחנו לא מניחים סלקטור אחד, מנסים כמה אפשרויות.
        # אם אף אחד לא עובד, נשמור דיבאג ואתה תגיד לי.
        filled = False
        selectors = [
            ('input[name="username"]', 'input[name="password"]'),
            ('input[type="text"]', 'input[type="password"]'),
            ('input[autocomplete="username"]', 'input[autocomplete="current-password"]'),
        ]

        for user_sel, pass_sel in selectors:
            try:
                page.wait_for_selector(user_sel, timeout=5000)
                page.wait_for_selector(pass_sel, timeout=5000)
                page.fill(user_sel, USER)
                page.fill(pass_sel, PWD)
                filled = True
                break
            except TimeoutError:
                continue

        if not filled:
            save_debug(page, ts, "mashov_login_fields_not_found")
            print("❌ Could not find login fields. Check artifacts/*fields_not_found*")
            context.close()
            return

        # 4) ללחוץ “כניסה”
        clicked = False
        # ננסה לפי כפתור submit
        try:
            page.locator('button[type="submit"]').first.click(timeout=2000)
            clicked = True
        except Exception:
            pass

        # ואם אין, ננסה לפי טקסטים נפוצים
        if not clicked:
            for name in ["כניסה", "התחבר", "Login", "Sign in"]:
                try:
                    btn = page.get_by_role("button", name=name)
                    if btn.count() > 0:
                        btn.first.click()
                        clicked = True
                        break
                except Exception:
                    pass

        if not clicked:
            save_debug(page, ts, "mashov_login_button_not_found")
            print("❌ Could not find login button. Check artifacts/*button_not_found*")
            context.close()
            return

        # 5) לחכות ניווט/דשבורד
        try:
            page.wait_for_load_state("networkidle", timeout=25000)
        except TimeoutError:
            pass

        # לפעמים נשארים באותו URL אבל מתחברים, אז ננסה לגשת לדשבורד שוב
        page.goto(DASH_URL, wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=25000)
        except TimeoutError:
            pass

        if is_logged_in(page):
            save_debug(page, ts, "mashov_logged_in_success")
            print("✅ Logged in successfully.")
        else:
            # אם יש קאפצ'ה/אימות נוסף/שגיאה – נשמור הכל
            save_debug(page, ts, "mashov_login_failed_or_challenge")
            print("⚠️ Login did not reach dashboard. Possible CAPTCHA/extra verification.")
            print("Check artifacts/mashov_login_failed_or_challenge_* (png+html)")

        context.close()

if __name__ == "__main__":
    main()