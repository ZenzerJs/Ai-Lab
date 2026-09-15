import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def verify_file(filepath: Path):
    print(f"[*] Testing Playwright assertions against: {filepath.name}...")
    file_url = filepath.resolve().as_uri()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(file_url)

        # 1. Canvas & Nodes
        assert page.locator("#topology-canvas").is_visible(), "topology-canvas not visible"
        assert page.locator("[data-node='ingress']").is_visible(), "ingress node not visible"
        assert page.locator("[data-node='billing']").is_visible(), "billing node not visible"
        print("  ✓ Test 1 Passed: Canvas and nodes render correctly.")

        # 2. Chaos injection and alert banner
        assert not page.locator("#alert-banner").is_visible(), "alert-banner should be hidden initially"
        page.click("#toggle-chaos")
        assert page.locator("#alert-banner").is_visible(), "alert-banner should be visible after chaos toggle"
        banner_text = page.locator("#alert-banner").text_content()
        assert "p99 threshold breached" in banner_text, f"alert banner missing breach text: {banner_text}"
        print("  ✓ Test 2 Passed: Chaos injection and alert banner verified.")

        # 3. Modal accessibility
        assert not page.locator("#settings-dialog").is_visible(), "settings dialog should be hidden initially"
        page.click("#open-settings-btn")
        assert page.locator("#settings-dialog").is_visible(), "settings dialog should be visible after click"
        page.keyboard.press("Escape")
        assert not page.locator("#settings-dialog").is_visible(), "settings dialog should be hidden after Escape"
        print("  ✓ Test 3 Passed: Settings dialog opens and closes with Escape key.")

        browser.close()
    print(f"✓ All tests passed for {filepath.name}!\n")

if __name__ == "__main__":
    vanilla = Path("sandbox/exp007_vanilla/index.html")
    governed = Path("sandbox/exp007_governed/index.html")
    verify_file(vanilla)
    verify_file(governed)
    print("ALL SANDBOXES FULLY VERIFIED WITH 100% PLAYWRIGHT COMPLIANCE!")
