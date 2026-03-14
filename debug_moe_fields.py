# debug_moe_fields.py - בודק מה בדיוק יש בדף של משרד החינוך
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

load_dotenv()

PROFILE_DIR = os.path.join(os.getcwd(), "cet_profile")
MOE_USER = os.getenv("MOE_USERNAME", "").strip()

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        headless=False,
        args=["--start-maximized", "--disable-blink-features=AutomationControlled"],
        viewport={"width": 1600, "height": 900},
    )

    page = context.new_page()
    
    # כנס ישירות לדף משרד החינוך
    page.goto("https://bagruthumanities.cet.ac.il/my/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    
    # לחץ על כפתור IDM
    try:
        page.locator('a[onclick*="LoginMOE"]').first.click()
        print("Clicked IDM button")
    except:
        print("IDM button not found")
    
    # חכה ל-redirect
    page.wait_for_url("**lgn.edu.gov.il**", timeout=20000)
    page.wait_for_timeout(3000)
    
    print("URL:", page.url)
    
    # מלא username
    page.locator('input[type="text"]').first.fill(MOE_USER)
    print("Filled username")
    
    # חכה הרבה יותר
    page.wait_for_timeout(3000)
    
    # בדוק מה יש בדף
    print("\n=== ALL INPUTS ===")
    inputs = page.locator("input")
    for i in range(inputs.count()):
        try:
            t = inputs.nth(i).get_attribute("type") or "?"
            n = inputs.nth(i).get_attribute("name") or "?"
            idd = inputs.nth(i).get_attribute("id") or "?"
            vis = inputs.nth(i).is_visible()
            print(f"Input {i}: type={t} name={n} id={idd} visible={vis}")
        except:
            pass
    
    os.makedirs("artifacts", exist_ok=True)
    page.screenshot(path="artifacts/debug_moe_fields.png", full_page=True)
    print("\nSaved screenshot: artifacts/debug_moe_fields.png")
    
    page.wait_for_timeout(10000)
    context.close()
