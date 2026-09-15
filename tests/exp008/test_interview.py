import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

def test_interview_flow_vanilla(page: Page):
    uri = Path("sandbox/exp008_vanilla/index.html").resolve().as_uri()
    page.goto(uri)
    page.click("#start-session-btn")
    expect(page.locator("#question-display")).to_be_visible()
    expect(page.locator("#evidence-card")).to_be_visible()
    for turn in range(1, 4):
        expect(page.locator("#turn-indicator")).to_have_text(f"Turn {turn} of 3")
        page.fill("#response-input", f"Turn {turn}: Implemented distributed state locks with atomic rollback.")
        page.click("#submit-turn-btn")
    expect(page.locator("#scorecard-dialog")).to_be_visible()
    expect(page.locator("#composite-score")).not_to_be_empty()

def test_interview_flow_governed(page: Page):
    uri = Path("sandbox/exp008_governed/index.html").resolve().as_uri()
    page.goto(uri)
    page.click("#start-session-btn")
    expect(page.locator("#question-display")).to_be_visible()
    expect(page.locator("#evidence-card")).to_be_visible()
    for turn in range(1, 4):
        expect(page.locator("#turn-indicator")).to_have_text(f"Turn {turn} of 3")
        page.fill("#response-input", f"Turn {turn}: Implemented distributed state locks with atomic rollback.")
        page.click("#submit-turn-btn")
    expect(page.locator("#scorecard-dialog")).to_be_visible()
    expect(page.locator("#composite-score")).not_to_be_empty()

