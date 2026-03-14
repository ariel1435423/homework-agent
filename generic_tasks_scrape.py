from playwright.sync_api import sync_playwright, TimeoutError
from datetime import datetime
import os
import re

PROFILE_DIR = os.path.join(os.getcwd(), "chrome_profile")

KEYWORDS = [
    "משימה", "מטלה", "הגשה", "להגיש", "שיעורי בית", "assignment", "assignments",
    "submission", "submit", "due", "תאריך הגשה"
]

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def scrape(page, ts: str, prefix: str):
    os.makedirs("artifacts", exist_ok=True)

    # מחכה קצת לטעינה דינמית
    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except TimeoutError:
        pass

    # צילום מסך תמיד
    page.screenshot(path=f"artifacts/{prefix}_{ts}.png", full_page=True)

    # אוסף קישורים וטקסטים
    anchors = page.locator("a")
    n = min(anchors.count(), 200)  # מספיק לרוב דפים

    hits = []
    for i in range(n):
        try:
            text = clean(anchors.nth(i).inner_text())
            href = anchors.nth(i).get_attribute("href") or ""
        except Exception:
            continue

        if not text:
            continue

        low = text.lower()
        if any(k.lower() in low for k in KEYWORDS):
            hits.append((text[:120], href))

    # אם לא מצא כלום, שמור HTML כדי להתאים סלקטורים בהמשך
    if not hits:
        html_path = f"artifacts/{prefix}_{ts}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(page.content())
        print(f"[{prefix}] No keyword hits. Saved HTML:", html_path)
        return []

    # ניקוי כפילויות
    seen = set()
    out = []
    for t, h in hits:
        key = (t, h)
        if key not in seen:
            seen.add(key)
            out.append({"title": t, "url": h})
    return out

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    targets = [
        ("mashov_tasks", "https://moodle.mashov.info/metro-west"),
        ("cet_tasks", "https://bagruthumanities.cet.ac.il"),
    ]

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = context.new_page()

        for prefix, url in targets:
            print("\nOpening:", url)
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(6000)

            tasks = scrape(page, ts, prefix)

            if tasks:
                print(f"[{prefix}] Found {len(tasks)} candidate items:")
                for t in tasks[:15]:
                    print("-", t["title"])
                    print("  ", t["url"])

        context.close()

if __name__ == "__main__":
    main()