# quick_mashov_moodle_tasks_debug.py
from playwright.sync_api import sync_playwright, TimeoutError
from dotenv import load_dotenv
import os

load_dotenv()

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")
LOGIN_URL = "https://web.mashov.info/students/login"
HOME_URL = "https://web.mashov.info/students/main/home"

USER = os.getenv("MASHOV_USERNAME", "").strip()
PWD = os.getenv("MASHOV_PASSWORD", "").strip()

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR, headless=False,
        args=["--start-maximized"],
        viewport={"width": 1600, "height": 900},
    )
    page = ctx.new_page()

    # 1) נסה להיכנס ל-HOME
    page.goto(HOME_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    # 2) טיפול ב-reauth popup
    if page.locator('text="נא להזדהות מחדש"').count() > 0:
        print("Reauth popup - filling password...")
        pw = page.locator('input[type="password"]:not([aria-hidden="true"])').first
        pw.wait_for(state="visible", timeout=8000)
        pw.fill(PWD)
        page.get_by_role("button", name="כניסה").first.click()
        page.wait_for_timeout(3000)

    # 3) אם בדף login - התחבר
    if "login" in page.url:
        print("Logging in...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        try:
            page.fill('input[name="username"]', USER)
            page.fill('input[name="password"]', PWD)
        except Exception:
            page.fill('input[type="text"]', USER)
            page.fill('input[type="password"]', PWD)
        try:
            page.locator('button[type="submit"]').first.click()
        except Exception:
            page.get_by_role("button", name="כניסה").click()
        page.wait_for_timeout(3000)
        page.goto(HOME_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

    print(f"Current URL: {page.url}")

    # 4) לחץ על "משימות Moodle"
    print("Clicking 'משימות Moodle'...")
    try:
        page.get_by_text("משימות Moodle", exact=True).click()
    except Exception:
        page.locator('text="משימות Moodle"').first.click()
    page.wait_for_timeout(5000)

    print(f"After click URL: {page.url}")

    # 5) שמור HTML + screenshot
    os.makedirs("artifacts", exist_ok=True)
    with open("artifacts/moodle_assignments_page.html", "w", encoding="utf-8") as f:
        f.write(page.content())
    page.screenshot(path="artifacts/moodle_assignments_page.png", full_page=True)
    print("Done! Saved to artifacts/moodle_assignments_page.html")

    page.wait_for_timeout(3000)
    ctx.close()
