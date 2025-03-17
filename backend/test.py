import uuid
import os
import random
import time
import asyncio
from playwright.async_api import async_playwright
from scraper.session_manager import SessionManager
from scraper.helpers import detect_and_click_button, count_execution_time,ensure_element_visible,click_button_strict
from scraper.ticket_data import extract_ticket_data, save_or_update_file

ZENROWS_API_KEY = "5301c7a60c1e5df1ba5aa297caa2e47b94de5a73"

async def scrape_with_session(url=None, session_name="default_session", output_filename=None, username=None, password=None, section=None, row=None):
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
        print("Connecting to Ticketmaster via ZenRows Proxy...")

        # browser = await p.chromium.launch(headless=False, proxy={
        #     "server": "http://64.112.56.196:23078",
        #     "username": "hZRIDCop",
        #     "password": "ZzLBTpTi"
        # })

        browser = await p.chromium.launch(headless=False)
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
            await page.wait_for_timeout(12000)
            print("Page loaded successfully, begin scraping...")

            await detect_and_click_button(
                page,
                xpath_selector='//button[@data-bdd="accept-modal-accept-button"]',
                description="Accept & Continue",
                optional=True,
                timeout=9000
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

            best_seats_selector = '//div[@data-bdd="sort-buttons-container"]//span[@data-bdd="quick-picks-sort-button-best"]'

            try:
                print("double check accept button")
                await detect_and_click_button(
                page,
                xpath_selector='//button[@data-bdd="accept-modal-accept-button"]',
                description="Accept & Continue",
                optional=True,
                timeout=3000
            )
                print("Checking for 'Best Seats' button...")
                await page.wait_for_selector(best_seats_selector, state='attached', timeout=10000)
                await detect_and_click_button(page, xpath_selector=best_seats_selector, description="BEST SEATS")
            except Exception as e:
                print(f"Warning: 'Best Seats' button not detected! Skipping... {e}")

            await page.wait_for_selector('div[data-bdd="merch-slot-title-vip-star"]', state='visible', timeout=16000)

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

                # if section and row:
                #     # section_row_selector = f'//div[@class="sc-564d33a0-5 bblocI"]//span[@aria-label="Sec {section} • Row {row}"]'
                #     section_row_selector = f'//div[@data-bbd="quick-pick-ticket-info"]//span[@aria-label="Sec {section} • Row {row}"]'
                #     try:
                #         print(f"Checking for section {section} and row {row}...")
                #         element = await page.query_selector(section_row_selector)
                #         if element:
                #             print(f"Section {section} and row {row} found, clicking...")
                #             await element.click()
                #             break
                #         else:
                #             print(f"Section {section} and row {row} not found, continuing to scroll...")
                #     except Exception as e:
                #         print(f"Warning: Unable to check for section {section} and row {row}! {e}")

            if not request_detected:
                print("Scrolling to the bottom to continue searching...")
                await press_end_button(page)
                await perform_random_wait('Scroll to bottom', timeout=2000)

                if section and row:
                    section_row_selector = f'//div[@data-bdd="quick-pick-ticket-info"]//span[@aria-label="Sec {section} • Row {row}"]'
                    try:
                        print(f"Checking for section {section} and row {row} after scrolling to the bottom...")
                        element = await page.query_selector(section_row_selector)
                        if element:
                            print(f"Section {section} and row {row} found, clicking...")
                            await element.click()
                        else:
                            print(f"Section {section} and row {row} not found after scrolling to the bottom.")
                    except Exception as e:
                        print(f"Warning: Unable to check for section {section} and row {row} after scrolling to the bottom! {e}")

            order_breakdown_button_selector = '//button[@data-bdd="order-breakdown-toggle-button"]'
            try:
                await ensure_element_visible(page, order_breakdown_button_selector, timeout=30000)
                print("Trying to click 'Order Breakdown' button...")
                # await detect_and_click_button(page, xpath_selector=order_breakdown_button_selector,description="Order Breakdown", timeout=20000)
                await click_button_strict(
                    page, 
                    xpath_selector='//button[@data-bdd="order-breakdown-toggle-button"]', 
                    description="Order Breakdown", 
                    index=1,
                    timeout=10000
                )

            except Exception as e:
                print(f"Warning: Unable to click 'Order Breakdown' button! {e}")

            try:
                await page.wait_for_selector('//div[@class="sc-1f896568-5 cNaoda" and contains(text(), "Face Value")]/following-sibling::div', state='visible', timeout=30000)
                face_value = await page.text_content('//div[@class="sc-1f896568-5 cNaoda" and contains(text(), "Face Value")]/following-sibling::div')
                service_fee = await page.text_content('//div[@class="sc-1f896568-5 cNaoda" and contains(text(), "Service Fee")]/following-sibling::div')
                order_processing_fee = await page.text_content('//div[@class="sc-1f896568-5 cNaoda" and contains(text(), "Order Processing Fee")]/following-sibling::div')

                print(f"Face Value: {face_value}")
                print(f"Service Fee: {service_fee}")
                print(f"Order Processing Fee: {order_processing_fee}")

            except Exception as e:
                print(f"Error extracting order breakdown data: {str(e)}")

            try:
                print("click button next")
                await(detect_and_click_button(page, xpath_selector='//button[@data-bdd="offer-card-buy-button"]', optional=True,description="Next", timeout=20000))
            except Exception as e:  
                print(f"Error clicking 'Next' button: {str(e)}")

        except Exception as e:
            print(f"Error during scraping: {str(e)}")
        finally:
            print("automate queue done! Press Enter to close the browser...")
            input()


if __name__ == "__main__":
    target_section = "319"
    target_row = "11"
    test_url = "https://www.ticketmaster.ca/linkin-park-from-zero-world-tour-vancouver-british-columbia-09-21-2025/event/1100616D8D0D22C7"
    asyncio.run(scrape_with_session(test_url, section=target_section, row=target_row, output_filename="test_output.json"))