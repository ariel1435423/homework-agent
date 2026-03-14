from playwright.sync_api import sync_playwright
from datetime import datetime
import os

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")  # פרופיל מקומי בתיקייה

def main():
    os.makedirs("artifacts", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = context.new_page()

        page.goto("https://classroom.google.com", wait_until="domcontentloaded")
        page.wait_for_timeout(4000)

        page.screenshot(path=f"artifacts/classroom_{ts}.png", full_page=True)

        # משאיר את הדפדפן פתוח שתוכל להתחבר אם צריך
        print("If you are not logged in, log in now in the opened browser window.")
        print("Close the browser window when done.")
        page.wait_for_timeout(120000)  # 2 דקות

        context.close()

if __name__ == "__main__":
    main()