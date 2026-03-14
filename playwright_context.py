import os


def get_storage_state_path() -> str | None:
    configured = os.getenv("AUTH_STATE_PATH", "").strip()
    candidates = [
        configured,
        os.path.join(os.getcwd(), "auth.json"),
    ]

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return None


def launch_browser_context(playwright, *, profile_dir: str, headless: bool, args: list[str], viewport: dict, label: str):
    storage_state_path = get_storage_state_path()
    if storage_state_path:
        browser = playwright.chromium.launch(
            headless=headless,
            args=args,
        )
        context = browser.new_context(
            viewport=viewport,
            storage_state=storage_state_path,
        )
        print(f"[{label}] Using auth state: {storage_state_path}")
        return browser, context

    context = playwright.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=headless,
        args=args,
        viewport=viewport,
    )
    return None, context


def close_browser_context(browser, context):
    try:
        context.close()
    finally:
        if browser:
            browser.close()
