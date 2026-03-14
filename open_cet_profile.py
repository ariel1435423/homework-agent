from playwright.sync_api import sync_playwright
import os

CET_MY_URL = "https://bagruthumanities.cet.ac.il/my/"
PROFILE_DIR = os.path.join(os.getcwd(), "cet_profile")

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--start-maximized"],
        viewport={"width": 1600, "height": 900},
    )

    page = context.new_page()
    page.goto(CET_MY_URL)

    print("Log in manually to CET (Digital Path). Then return here.")
    print("Keep the browser open ~20 seconds after login, then close it yourself.")
    page.wait_for_timeout(600000)  # 10 דקות