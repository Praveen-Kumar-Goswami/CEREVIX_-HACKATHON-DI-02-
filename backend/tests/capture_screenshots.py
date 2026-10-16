"""
Capture screenshots for delivery verification
"""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path


async def capture_screenshots():
    """Capture screenshots of key pages"""
    screenshots_dir = Path(__file__).parent.parent.parent / "docs" / "delivery_screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # Homepage
        print("Capturing homepage...")
        await page.goto('http://localhost:8000/index.html')
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(screenshots_dir / "01_homepage.png"), full_page=True)
        
        # Homepage with upload section focused
        print("Capturing upload interface...")
        await page.evaluate('document.getElementById("t1ce").scrollIntoView()')
        await page.wait_for_timeout(500)
        await page.screenshot(path=str(screenshots_dir / "02_upload_interface.png"), full_page=True)
        
        # 3D viewer page
        print("Capturing 3D viewer...")
        await page.goto('http://localhost:8000/3d-brain-viewer.html?case_id=test')
        await page.wait_for_timeout(3000)
        await page.screenshot(path=str(screenshots_dir / "03_3d_viewer.png"), full_page=True)
        
        await browser.close()
        print(f"Screenshots saved to {screenshots_dir}")


if __name__ == '__main__':
    asyncio.run(capture_screenshots())
