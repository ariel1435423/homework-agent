from playwright.sync_api import sync_playwright
from datetime import datetime
import os

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")

def main():
    os.makedirs("artifacts", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = context.new_page()

        page.goto("https://moodle.mashov.info/metro-west", wait_until="domcontentloaded")
        page.wait_for_timeout(6000)

        page.screenshot(path=f"artifacts/mashov_{ts}.png", full_page=True)

        print("If login is required, log in now. Then navigate to the page where assignments are listed.")
        print("Close the browser window when done.")
        page.wait_for_timeout(180000)  # 3 דקות

        context.close()

if __name__ == "__main__":
    main()