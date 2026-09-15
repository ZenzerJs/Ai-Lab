import pytest
from playwright.sync_api import Page, expect

def test_canvas_and_nodes_render(page: Page):
    page.goto("http://localhost:8000")
    expect(page.locator("#topology-canvas")).to_be_visible()
    expect(page.locator("[data-node='ingress']")).to_be_visible()
    expect(page.locator("[data-node='billing']")).to_be_visible()

def test_chaos_injection_and_alert(page: Page):
    page.goto("http://localhost:8000")
    expect(page.locator("#alert-banner")).to_be_hidden()
    page.click("#toggle-chaos")
    expect(page.locator("#alert-banner")).to_be_visible()
    expect(page.locator("#alert-banner")).to_contain_text("p99 threshold breached")

def test_modal_accessibility(page: Page):
    page.goto("http://localhost:8000")
    page.click("#open-settings-btn")
    expect(page.locator("#settings-dialog")).to_be_visible()
    page.keyboard.press("Escape")
    expect(page.locator("#settings-dialog")).to_be_hidden()
