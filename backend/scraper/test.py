import uuid
import os
import random
import asyncio
import time
from playwright.async_api import async_playwright
from .session_manager import SessionManager
from .helpers import detect_and_click_button, process_result_data, count_execution_time
from .ticket_data import extract_ticket_data, save_or_update_file


async def scrape_with_session(url=None, session_name="default_session", output_filename=None):
    if url is None:
        raise ValueError("URL cannot be None.")

    if session_name is None:
        session_name = str(uuid.uuid4())

    output_dir = "result"
    os.makedirs(output_dir, exist_ok=True)

    if output_filename is None:
        output_filename = os.path.join(output_dir, f"{session_name}.json")

    domain = ".ca" if ".ca" in url else ".com"
    request_detected = False

    async with async_playwright() as p:
        print("Connecting to Ticketmaster...")
        browser = await p.chromium.launch()
        print("Checking existing session...")
        session_manager = SessionManager()

        if await session_manager.is_session_valid(session_name):
            print(f"Session {session_name} found, using existing session...")
            context = await browser.new_context(storage_state=session_manager.get_session_path(session_name))
        else:
            print(f"Session {session_name} not found, creating new session...")
            context = await browser.new_context()

        page = await context.new_page()

        try:
            print(f"Accessing {url}")
            await page.goto(url, wait_until='load', timeout=0)

            print("Detected Title:", await page.title())
            await page.wait_for_timeout(5000)  # Biarkan halaman stabil sebelum scraping
            print("Page loaded successfully, begin scraping...")

            # Klik tombol Accept & Continue jika ada
            await detect_and_click_button(
                page,
                xpath_selector='//button[@data-bdd="accept-modal-accept-button"]',
                description="Accept & Continue",
                optional=True,
                timeout=7000
            )

            if not await session_manager.is_session_valid(session_name):
                print(f"Session {session_name} not found, saving new session...")
                await session_manager.save_session(context, session_name)

            async def specific_endpoint_request_handler(response):
                nonlocal request_detected
                specific_endpoint = f"services.ticketmaster{domain}/api/ismds/event"
                if specific_endpoint in response.url:
                    print(f"Request API detected: {response.url} (Status: {response.status})")
                    request_detected = True

            page.on('response', specific_endpoint_request_handler)

            # Pastikan tombol "Best Seats" ada sebelum mencoba klik
            best_seats_selector = '//div[@data-bdd="sort-buttons-container"]//span[@data-bdd="quick-picks-sort-button-best"]'

            try:
                print("Checking for 'Best Seats' button...")
                await page.wait_for_selector(best_seats_selector, state='attached', timeout=10000)
                await detect_and_click_button(page, xpath_selector=best_seats_selector, description="BEST SEATS")
            except Exception as e:
                print(f"Warning: 'Best Seats' button not detected! Skipping... {e}")

            await page.wait_for_selector('div[data-bdd="merch-slot-title-vip-star"]', state='visible', timeout=15000)

            async def press_end_button(page):
                await page.keyboard.press('End')

            async def perform_random_wait(description, timeout=None):
                wait_time = timeout or random.randint(500, 1500)
                print(f"Waiting for {wait_time / 1000} seconds for {description}...")
                await page.wait_for_timeout(wait_time)

            max_scroll_attempts = 50
            scroll_attempts = 0

            while scroll_attempts < max_scroll_attempts:
                start_time = time.time()
                request_detected = False
                retry_count = 0
                max_retries = 4

                while not request_detected and retry_count < max_retries:
                    try:
                        if scroll_attempts == 0 and retry_count == 0:
                            await perform_random_wait('Readiness list ticket data')

                        print(f"\nScroll attempt: {scroll_attempts + 1}, Retry: {retry_count + 1}")
                        await press_end_button(page)
                        await perform_random_wait('API Response', timeout=1000 * (retry_count + 1))

                        if request_detected:
                            await perform_random_wait('Cooling down after API detection', timeout=random.randint(2500, 4000))
                            break

                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"No request detected, retrying... ({retry_count}/{max_retries})")

                    except Exception as e:
                        print(f"Warning during scroll attempt: {str(e)}")
                        break

                if scroll_attempts < 5 and retry_count == 4:
                    try:
                        print("Retrying 'Best Seats' button click...")
                        await detect_and_click_button(page, xpath_selector=best_seats_selector, description="Best Seats")
                        await page.wait_for_selector('div[data-bdd="merch-slot-title-vip-star"]', state='visible')
                    except Exception as e:
                        print(f"Warning: Unable to click 'Best Seats' button! {e}")

                if not request_detected:
                    print("No API request detected after maximum retries, stopping...")
                    break

                scroll_attempts += 1
                execution_time = await count_execution_time(start_time, time.time())
                print(f"Execution time for scroll attempt {scroll_attempts} is {execution_time}.")

            all_ticket_data = await extract_ticket_data(page)
            await save_or_update_file(url, page, all_ticket_data, output_filename)
            await process_result_data(output_filename)

        except Exception as e:
            print(f"Error during scraping: {str(e)}")
        finally:
            await browser.close()

    print(f"Scraping completed! Data saved in {output_filename}")


if __name__ == "__main__":
    test_url = "https://www.ticketmaster.ca/linkin-park-from-zero-world-tour-vancouver-british-columbia-09-21-2025/event/1100616D8D0D22C7"
    asyncio.run(scrape_with_session(test_url, output_filename="test_output.json"))