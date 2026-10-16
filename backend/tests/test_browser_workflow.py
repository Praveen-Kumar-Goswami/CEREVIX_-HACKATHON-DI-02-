"""
Browser workflow tests for NeuroScope 3D
Tests the complete frontend application using Playwright
"""

import asyncio
from playwright.async_api import async_playwright, expect
import pytest
import time


@pytest.mark.asyncio
async def test_homepage_loads():
    """Test that the homepage loads without fatal errors"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to homepage
        await page.goto('http://localhost:8000/index.html')
        
        # Check page title
        title = await page.title()
        assert 'NeuroScope' in title
        
        # Check for fatal errors
        errors = []
        page.on('console', lambda msg: errors.append(msg) if msg.type == 'error' else None)
        
        await page.wait_for_timeout(2000)
        
        # Should not have fatal errors
        fatal_errors = [e for e in errors if 'fatal' in str(e).lower()]
        assert len(fatal_errors) == 0, f"Fatal errors found: {fatal_errors}"
        
        await browser.close()


@pytest.mark.asyncio
async def test_upload_interface_visible():
    """Test that upload interface appears correctly"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8000/index.html')
        
        # Check for upload section
        upload_section = page.locator('text=Upload MRI Scans')
        await expect(upload_section).to_be_visible()
        
        # Check for 4 file inputs
        t1ce_input = page.locator('input[id="t1ce"]')
        t1_input = page.locator('input[id="t1"]')
        t2_input = page.locator('input[id="t2"]')
        flair_input = page.locator('input[id="flair"]')
        
        await expect(t1ce_input).to_be_visible()
        await expect(t1_input).to_be_visible()
        await expect(t2_input).to_be_visible()
        await expect(flair_input).to_be_visible()
        
        # Check for upload button
        upload_btn = page.locator('button:has-text("Upload and Process")')
        await expect(upload_btn).to_be_visible()
        
        await browser.close()


@pytest.mark.asyncio
async def test_disclaimer_visible():
    """Test that research disclaimer is visible"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8000/index.html')
        
        # Check for disclaimer
        disclaimer = page.locator('text=RESEARCH USE ONLY')
        await expect(disclaimer).to_be_visible()
        
        await browser.close()


@pytest.mark.asyncio
async def test_niivue_loads():
    """Test that NiiVue library loads"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8000/index.html')
        
        # Wait for NiiVue to load
        await page.wait_for_timeout(2000)
        
        # Check if NiiVue is available
        niivue_available = await page.evaluate('typeof niivue !== "undefined"')
        assert niivue_available, "NiiVue library not loaded"
        
        await browser.close()


@pytest.mark.asyncio
async def test_3d_viewer_loads():
    """Test that 3D viewer page loads"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto('http://localhost:8000/3d-brain-viewer.html?case_id=test')
        
        # Check page title
        title = await page.title()
        assert 'NeuroScope' in title
        
        # Check for Three.js
        await page.wait_for_timeout(2000)
        three_available = await page.evaluate('typeof THREE !== "undefined"')
        assert three_available, "Three.js library not loaded"
        
        await browser.close()


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
