import uuid
import os
import random
import time
from playwright.async_api import async_playwright
from .session_manager import SessionManager
from .helpers import detect_and_click_button, process_result_data, count_execution_time,ensure_element_visible,click_button_strict,custom_human_scroll
from .ticket_data import extract_ticket_data, save_or_update_file

ZENROWS_API_KEY = "5301c7a60c1e5df1ba5aa297caa2e47b94de5a73"

async def scrape_with_session(url=None, session_name="default_session",target_section=None,target_row=None, output_filename=None):
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
        
        browser = await p.firefox.launch( 
            headless=False, 
            proxy = {
            "server": "http://139.64.236.93:45840",  
            "username": "ioRa977S",
            "password": "GIzlQWTg"
          }
          )
        # browser = await p.chromium.launch(headless=False)
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
            await page.goto(url, timeout=0)

            print("Detected Title:", await page.title())
            await page.wait_for_timeout(10000)  
            print("Page loaded successfully, begin scraping...")

            await detect_and_click_button(
                page,
                xpath_selector='//button[@data-bdd="accept-modal-accept-button"]',
                description="Accept & Continue",
                optional=True,
                timeout=13000
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
                await page.wait_for_selector(best_seats_selector, state='attached', timeout=12000)
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
            
            if target_section and target_row:
                    section = target_section
                    row = target_row
                    print(section,row)
                    section_row_selector = f'//div[@data-bdd="quick-pick-ticket-info"]//span[@aria-label="Sec {section} • Row {row}"]'
                    try:
                        print(f"Checking for section {section} and row {row} after scrolling to the bottom...")
                        element = await page.query_selector(section_row_selector)
                        if element:
                            print(f"Section {section} and row {row} found, clicking...")
                            await element.click()
                        else:
                            print(f"Section {section} and row {row} Not found after scroll API, trying manual scrolling..")
                            custom_scroll = 'div[data-bdd="qp-split-scroll"]'
                            await custom_human_scroll(page,custom_scroll)  
                            print(f"Retrying to found section {section} and row {row} After manual scrolling...")
                            element = await page.query_selector(section_row_selector)

                            if element:
                                print(f"Section {section} and row {row} found after Human Scroll ! Clicking...")
                                await element.click()
                            else:
                                print(f"Section {section} and row {row} Still Not Found After Human scrolling . Stopping ...")

                    except Exception as e:
                        print(f"Warning: Unable to check for section {section} and row {row} after scrolling to the bottom! {e}")

                    order_breakdown_button_selector = '//button[@data-bdd="order-breakdown-toggle-button"]'
                    try:
                        await ensure_element_visible(page, order_breakdown_button_selector, timeout=30000)
                        print("Trying to click 'Order Breakdown' button...")
                        await click_button_strict(
                            page,
                            xpath_selector="//button[@data-bdd='order-breakdown-toggle-button']",
                            description="Order Breakdown",
                            index=0,  
                            timeout=10000
                        )

                    except Exception as e:
                        print(f"Warning: Unable to click 'Order Breakdown' button! {e}")

                    try:
                        # await page.wait_for_selector('//div[@class="sc-1f896568-5 cNaoda" and contains(normalize-space(.), "Face Value")]/following-sibling::div[1]', state='visible', timeout=30000)
                        face_value = await page.text_content('//div[@class="sc-1f896568-3 khExAn"][div/div[contains(text(), "Face Value")]]/div[@class="sc-1f896568-5 cNaoda"][last()]')
                        service_fee = await page.text_content('//div[@class="sc-1f896568-3 khExAn"][div/div[contains(text(), "Service Fee")]]/div[@class="sc-1f896568-5 cNaoda"][last()]')
                        order_processing_fee =await page.text_content('//div[@class="sc-1f896568-3 khExAn"][div/div[contains(text(), "Order Processing Fee")]]/div[@class="sc-1f896568-5 cNaoda"][last()]')


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
            

                    email = "Benjamin.Tan@swastamita.com"
                    password = "NaikMobil123!"
                    try:
                            print("Navigating to login page...")
                            form_login = '//button[data-bdd="sign-in-button"]'
                            await ensure_element_visible(page, form_login, timeout=50000)
                            await page.wait_for_selector('input[data-bdd="email-address-field"]', state="visible", timeout=10000)
                            
                            print("Filling in email...")
                            await ensure_element_visible(page, form_login, timeout=2000)
                            await page.fill('input[data-bdd="email-address-field"]', email)
                            await page.wait_for_selector('button[data-bdd="sign-in-button"]', state="visible", timeout=1000)
                            await page.click('button[data-bdd="sign-in-button"]')
                            
                            print("Filling in password...")
                            await page.wait_for_selector('input[data-bdd="password-field"]', state="visible", timeout=10000)
                            await page.fill('input[data-bdd="password-field"]', password)

                            await page.wait_for_selector('button[data-bdd="sign-in-button"]', state="visible", timeout=10000)
                            print("Clicking sign-in button...")
                            await page.click('button[data-bdd="sign-in-button"]')

                            await page.wait_for_timeout(3000)
                            print("Login attempt completed.")

                    except Exception as e:
                        print(f"Error during login: {str(e)}")

                    print("Extracting ticket data...")    
            else:
                all_ticket_data = await extract_ticket_data(page)
                await save_or_update_file(url, page, all_ticket_data, output_filename)
                await process_result_data(output_filename)

        except Exception as e:
                print(f"Error during scraping: {str(e)}")
        finally:
                await browser.close()

        print(f"Scraping completed! Data saved in {output_filename}")
