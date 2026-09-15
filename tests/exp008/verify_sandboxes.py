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

        # 1. Start session button and initial state
        assert page.locator("#start-session-btn").is_visible(), "start-session-btn not visible initially"
        page.click("#start-session-btn")
        
        assert page.locator("#question-display").is_visible(), "question-display not visible after start"
        assert page.locator("#evidence-card").is_visible(), "evidence-card not visible after start"
        print("  ✓ Assertion 1 Passed: Session initialized with question and evidence card.")

        # 2. Interactive 3-turn submission progression
        for turn in range(1, 4):
            expected_indicator = f"Turn {turn} of 3"
            assert page.locator("#turn-indicator").inner_text() == expected_indicator, f"Expected {expected_indicator}, got {page.locator('#turn-indicator').inner_text()}"
            page.fill("#response-input", f"Turn {turn}: Implemented distributed state locks with atomic rollback.")
            page.click("#submit-turn-btn")
            print(f"  ✓ Assertion 2.{turn} Passed: Turn {turn} submitted successfully.")

        # 3. Final rubric scorecard dialog
        assert page.locator("#scorecard-dialog").is_visible(), "scorecard-dialog not visible after 3 turns"
        score_text = page.locator("#composite-score").inner_text().strip()
        assert len(score_text) > 0, "composite-score element is empty"
        print(f"  ✓ Assertion 3 Passed: Scorecard modal visible with composite score: {score_text}")

        browser.close()
    print(f"✓ All Playwright tests passed for {filepath.name}!\n")

if __name__ == "__main__":
    vanilla = Path("sandbox/exp008_vanilla/index.html")
    governed = Path("sandbox/exp008_governed/index.html")
    verify_file(vanilla)
    verify_file(governed)
    print("ALL EXP-008 SANDBOXES FULLY VERIFIED WITH 100% PLAYWRIGHT COMPLIANCE!")

