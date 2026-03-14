from playwright.sync_api import sync_playwright, TimeoutError
from datetime import datetime
import os

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")
MASHOV_LOGIN = "https://web.mashov.info/students/login"

def save_debug(page, ts, prefix):
    os.makedirs("artifacts", exist_ok=True)
    page.screenshot(path=f"artifacts/{prefix}_{ts}.png", full_page=True)
    with open(f"artifacts/{prefix}_{ts}.html", "w", encoding="utf-8") as f:
        f.write(page.content())

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            args=["--start-maximized"],
            viewport={"width": 1600, "height": 900},
        )

        page = context.new_page()

        # 1) עמוד התחברות הנכון
        page.goto(MASHOV_LOGIN, wait_until="domcontentloaded")

        # 2) לתת זמן לטעינות SPA/iframes (כולל CAPTCHA)
        try:
            page.wait_for_load_state("networkidle", timeout=25000)
        except TimeoutError:
            pass

        # תיעוד לפני התחברות
        save_debug(page, ts, "mashov_login_opened")

        print("Mashov login page opened.")
        print("👉 Log in manually in the browser window.")
        print("👉 If it asks for CAPTCHA, scroll a bit and wait 20–30 seconds for it to appear.")
        print("👉 When you finish login and see your dashboard/home, come back here.")
        input("Press ENTER after you are logged in...")

        # תיעוד אחרי התחברות
        save_debug(page, ts, "mashov_after_login")

        print("OK. Session should now be saved in chrome_profile.")
        input("Press ENTER to close the browser...")

        context.close()

if __name__ == "__main__":
    main()