import asyncio
from playwright.async_api import async_playwright


async def scrape_footystream():
    """
    Download the HTML body from footystream.pk
    """
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Navigating to FootyStream...")
        await page.goto('https://footystream.pk/soccer-streams', wait_until='networkidle')
        
        print("Waiting for page to load completely...")
        await asyncio.sleep(3)  # Wait additional 3 seconds for any dynamic content
        
        print("Extracting body HTML...")
        
        # Get the body HTML
        body_html = await page.evaluate('() => document.body.innerHTML')
        
        await browser.close()
        
        return body_html


# async def main():
#     """Main function to run the scraper"""
#     print("FootyStream HTML Body Downloader")
#     print("="*80 + "\n")
    
#     # Get the body HTML
#     body_html = await scrape_footystream()
    
#     # Save to file
#     with open('body_content.html', 'w', encoding='utf-8') as f:
#         f.write(body_html)
    
#     print(f"\n✓ Body HTML saved to: body_content.html")
#     print(f"✓ Total length: {len(body_html)} characters")
    
#     # Print first 3000 characters to console
#     print("\n" + "="*80)
#     print("FIRST 3000 CHARACTERS OF BODY HTML:")
#     print("="*80)
#     print(body_html[:3000])
#     print("="*80)
#     print("\n✓ Check body_content.html for the complete HTML")


# if __name__ == "__main__":
#     asyncio.run(main())