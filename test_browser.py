from playwright.sync_api import sync_playwright
from datetime import datetime
import os

def main():
    os.makedirs("artifacts", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # רואים חלון
        context = browser.new_context()
        page = context.new_page()

        page.goto("https://www.google.com", wait_until="domcontentloaded")
        page.wait_for_timeout(1500)

        page.screenshot(path=f"artifacts/google_{ts}.png", full_page=True)

        context.close()
        browser.close()

if __name__ == "__main__":
    main()