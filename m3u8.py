import asyncio
from playwright.async_api import async_playwright

real_chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

async def scrape_m3u8(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            # executable_path=real_chrome
        )

        page = await browser.new_page()

        loop = asyncio.get_running_loop()
        future = loop.create_future()

        async def handle_response(response):
            if (
                ".m3u8" in response.url
                and response.request.resource_type == "xhr"
                and response.status == 200
            ):
                if not future.done():
                    future.set_result({
                        "m3u8": response.url,
                        "headers": dict(response.request.headers)
                        
                    })

        page.on("response", handle_response)

        await page.goto(url)

        try:
            result = await asyncio.wait_for(future, timeout=20)
        except asyncio.TimeoutError:
            result = {"m3u8": None, "headers": None}

        await browser.close()
        return result


# # ---- RUN & PRINT RESULT ----
# if __name__ == "__main__":
#     url = "https://footystream.top/alpha/atp-tennis/12353"

#     result = asyncio.run(scrape_m3u8(url))

#     print("\n=== SCRAPE RESULT ===")
#     print("M3U8 URL:", result["m3u8"])
#     print("Headers:", result["headers"])
