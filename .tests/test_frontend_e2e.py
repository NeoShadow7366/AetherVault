import pytest
from playwright.sync_api import Page, expect

def test_page_loads_and_has_title(page: Page):
    """Verifies that the monolith index.html loads and rendering initializes."""
    page.goto("/")
    expect(page).to_have_title("AI Manager Dashboard")
    expect(page.locator("h1#page-title")).to_have_text("Model Explorer")

def test_tab_navigation_ui(page: Page):
    """Clicks the sidebar tabs safely and asserts that JavaScript switches the UI context."""
    page.goto("/")
    
    # Model Explorer starts visible. We check its identifier
    explorer_view = page.locator("#view-explorer")
    vault_view = page.locator("#view-vault")
    
    expect(explorer_view).to_be_visible()
    expect(vault_view).to_be_hidden()
    
    # Click Global Vault in sidebar — use exact=True to avoid matching
    # "Symlink Global Vault Folders" label and export description
    page.get_by_text("Global Vault", exact=True).click()
    
    # The active view should toggle via main.js
    expect(explorer_view).to_be_hidden()
    expect(vault_view).to_be_visible()
    expect(page.locator("h1#page-title")).to_have_text("Global Vault")

def test_theme_switch(page: Page):
    """Asserts that picking a new dropdown theme applies the CSS [data-theme] securely."""
    page.goto("/")
    
    # Navigate to Settings tab (unified settings panel, no longer a modal)
    page.locator(".nav-item", has_text="Settings").click()
    
    # Wait for the settings view to be visible
    page.locator("#view-settings").wait_for(state="visible")
    
    # Open dropdown, select Light Mode
    page.locator("#set-theme").select_option(value="light", force=True)
    
    # Fire the Settings native global save function securely
    page.evaluate("saveSettings()")
    
    # Check that document root updated its attribute
    expect(page.locator("body")).to_have_attribute("data-theme", "light")
    
    # Switch back to dark to ensure toggle works
    page.locator("#set-theme").select_option(value="dark", force=True)
    page.evaluate("saveSettings()")
    expect(page.locator("body")).to_have_attribute("data-theme", "dark")

def test_api_key_modal(page: Page):
    """Verifies the CivitAI Settings button navigates to the unified Settings tab."""
    page.goto("/")
    
    # The CivitAI Settings toolbar button now calls toggleSettings()
    # which navigates to the unified Settings tab (no longer opens a modal)
    settings_btn = page.locator("button[title='CivitAI Settings']")
    settings_btn.click()
    
    # Verify we're now on the Settings tab
    settings_view = page.locator("#view-settings")
    expect(settings_view).to_be_visible()
    expect(page.locator("h1#page-title")).to_have_text("Settings")
    
    # Verify the API key input is present and editable
    api_input = page.locator("#set-api-key")
    expect(api_input).to_be_visible()
