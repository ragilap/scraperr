from playwright.async_api import async_playwright
from session_manager import SessionManager
from helpers import detect_and_click_button, process_result_data, count_execution_time, read_json_async
from ticket_data import extract_ticket_data, save_or_update_file
from datetime import datetime
import random
import time
from urllib.parse import urlparse
import asyncio

async def scrape_with_session(url=None, session_name="default_session", headless=False, email_account="xx@gmail.com", password_account="NaikMobil123!"):
    if url == None:
        raise ValueError("URL cannot be None.")
    domain = ".ca" if ".ca" in url else ".com"
    request_detected = False

    # Buat nama file dengan timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"result/ticket_data_{timestamp}.json"

    proxies = [
        "139.64.236.92:48138:ioRa977S:GIzlQWTg",
        "139.64.236.93:45840:ioRa977S:GIzlQWTg",
        "139.64.236.94:31846:ioRa977S:GIzlQWTg",
        "139.64.236.95:31745:ioRa977S:GIzlQWTg",
        "139.64.236.96:41168:ioRa977S:GIzlQWTg",
        "139.64.236.97:33924:ioRa977S:GIzlQWTg",
        "139.64.236.103:40942:ioRa977S:GIzlQWTg",
        "139.64.236.104:49827:ioRa977S:GIzlQWTg",
        "139.64.236.105:36095:ioRa977S:GIzlQWTg",
        "139.64.236.106:29294:ioRa977S:GIzlQWTg"
    ]

    def random_proxy_picker():
        return random.choice(proxies)

    async with async_playwright() as p:
        print("Pick proxy...")
        selected_proxy = random_proxy_picker()
        ip, port, username, password = selected_proxy.split(":")
        proxy = {
            "server": f"http://{ip}:{port}",
            "username": username,
            "password": password
        }
        print(f"Picked proxy IP:Port is {ip}:{port}")
        print("Opening browser...")
        browser = await p.chromium.launch(headless=headless, proxy=proxy)

        is_session_valid = False

        print("Checking existing session...")
        session_manager = SessionManager()
        if await session_manager.is_session_valid(session_name):
            print("Session valid founded, using existing session...")
            context = await browser.new_context(
                storage_state=session_manager.get_session_path(session_name),
                # user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
                locale="en-US"
            )
            is_session_valid = True
        else:
            print("Session valid not found, generate new session...")
            context = await browser.new_context(
                # user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0",
                locale="en-US"
            )

        page = await context.new_page()

        if not is_session_valid:
            async def perform_login():
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                print(f"Accessing {base_url}")
                print("Waiting for home page load...")
                await page.goto(base_url, wait_until='load', timeout=0)
                await detect_and_click_button(page, xpath_selector='//button[@data-testid="accountLink"]', description="Sign In / Register")

                print("Delay prewaiting to login page load...")
                await page.wait_for_timeout(10000)
                print("Waiting for login page load...")
                await page.wait_for_load_state('load', timeout=0)

                print("Delay prewaiting to login page second load...")
                await page.wait_for_timeout(10000)
                print("Waiting for login page second load...")
                await page.wait_for_load_state('load', timeout=0)
                
                print("Begin filling email and password")
                await page.locator("//input[@name='email']").fill(email_account)
                await detect_and_click_button(page, xpath_selector="//button[@data-bdd='sign-in-button']", description="Continue to Input Password")
                await page.wait_for_selector("//input[@data-bdd='password-field']", state="visible")
                await page.locator("//input[@data-bdd='password-field']").fill(password_account)
                await detect_and_click_button(page, xpath_selector="//button[@data-bdd='sign-in-button']", description="Sign In")

                print("Delay prewaiting after login...")
                await page.wait_for_timeout(10000)
                print("Waiting for home page load...")
                await page.wait_for_load_state('load', timeout=0)
                if not await session_manager.is_session_valid(session_name):
                    print("Saving new session...")
                    await session_manager.save_session(context, session_name)
                    print("New session has been saved...")
                print("Finish login. continue to the next process")

            await perform_login()

        try:
            print(f"Accessing {url}")
            print("Waiting for first load...")
            await page.goto(url, wait_until='load', timeout=0)
            print("Detected Title:", await page.title())
            print("Delay prewaiting to second load...")
            await page.wait_for_timeout(10000)
            print("Detected Title:", await page.title())

            async def get_countdown_values(page):
                try:
                    days = int(await page.locator('[data-bdd="countdown-timer-days"]').inner_text())
                    hours = int(await page.locator('[data-bdd="countdown-timer-hours"]').inner_text())
                    minutes = int(await page.locator('[data-bdd="countdown-timer-minutes"]').inner_text())
                    seconds = int(await page.locator('[data-bdd="countdown-timer-seconds"]').inner_text())
                    return days, hours, minutes, seconds
                except:
                    return None
            
            async def wait_countdown():
                while True:
                    values = await get_countdown_values(page)
                    if values is None:
                        print("Could not retrieve countdown values.")
                        return False

                    days, hours, minutes, seconds = values
                    print(f"Countdown: {days}d {hours}h {minutes}m {seconds}s")

                    if days == 0 and hours == 0 and minutes == 0 and seconds == 0:
                        print("Countdown complete.")
                        return True

                    await asyncio.sleep(1)

            countdown = page.locator('[data-bdd="countdown-timer"]')
            if await countdown.count() > 0:
                print("Countdown timer found. Waiting for countdown...")
                is_countdown_complete = await wait_countdown()
                if is_countdown_complete:
                    print("Delay prewaiting to second load...")
                    await page.wait_for_timeout(10000)
            
            join_waiting_room_button = page.locator('[data-bdd="lobby-card-CTAButton"]', has_text="Join Waiting Room")
            if await join_waiting_room_button.count() > 0:
                print("Join waiting room found.")
                await detect_and_click_button(page, xpath_selector='//button[@data-bdd="lobby-card-CTAButton" and .//text()="Join Waiting Room"]', description="Join Waiting Room")
                await page.wait_for_load_state('load', timeout=0)
                await page.wait_for_timeout(10000)
                await page.wait_for_load_state('load', timeout=0)
            
            join_waiting_queue_button = page.locator('[data-bdd="lobby-card-CTAButton"]', has_text="Join the Queue")
            if await join_waiting_queue_button.count() > 0:
                print("Join the queue found.")
                await detect_and_click_button(page, xpath_selector='//button[@data-bdd="lobby-card-CTAButton" and .//text()="Join the Queue"]', description="Join the Queue")
                try:
                    await page.wait_for_selector('h2[data-bdd="mfa-authenticate-header"]', state='visible', timeout=30000)
                except TimeoutError:
                    print("MFA header not visible after 30 seconds, trying 'attached' state as fallback...")
                    await page.wait_for_selector('h2[data-bdd="mfa-authenticate-header"]', state='attached', timeout=30000)

            auth_header = page.locator('//h2[@data-bdd="mfa-authenticate-header"]')
            if await auth_header.count() > 0:
                print("MFA authentication found.")
                await detect_and_click_button(page, xpath_selector='//input[@type="radio" and @data-bdd="mfa-email-radio-button" and @value="EMAIL"]', description="MFA Email")
                await detect_and_click_button(page, xpath_selector='//button[@type="submit" and @data-bdd="mfa-next-button" and .//text()="Next"]', description="MFA Next")
                await page.wait_for_load_state('load', timeout=0)
                await page.wait_for_timeout(60000)
                await page.wait_for_load_state('load', timeout=0)

            print("Waiting for second load...")
            await page.wait_for_load_state('load', timeout=0)
            print("Detected Title:", await page.title())

            title = await page.title()
            if title == 'Your Browsing Activity Has Been Paused':
                raise ConnectionError("DETECTED AS BOT!")

            print("Page loaded successfully, begin scraping...")
            await detect_and_click_button(page, xpath_selector='//button[@data-bdd="accept-modal-accept-button"]', description="Accept & Continue", optional=True, timeout=7000)
            
            async def specific_endpoint_request_handler(response):
                """Detect request and handle the response"""
                # Access request_detected variable outside function
                nonlocal request_detected
                # Detect specific endpoint request in response url after click best seats or perform scrolling
                specific_endpoint = f"services.ticketmaster{domain}/api/ismds/event" if domain == ".ca" else f"services.ticketmaster.com/api/ismds/event"
                if specific_endpoint in response.url:
                    print(f"Request API detected: {response.url}")
                    print(f"Status: {response.status}")
                    request_detected = True

            # Detect and click the 'Best Seats' button if it appears
            await detect_and_click_button(page, xpath_selector='//span[@data-bdd="quick-picks-sort-button-best"]', description="Best Seats")

            # Wait vip star row visible
            await page.wait_for_selector('div[data-bdd="quick-pick-ticket-info"]', state='visible')

            page.on('response', specific_endpoint_request_handler)

            async def prevent_upward_scroll(page):
                await page.evaluate("""
                    window.addEventListener('wheel', function(event) {
                        if (event.deltaY < 0) {  // Check if the scroll direction is upwards
                            event.preventDefault();  // Prevent the scroll
                        }
                    }, { passive: false });
                """)

            async def press_end_button(page):
                await page.keyboard.press('End')
            
            async def perform_random_wait(page, description, timeout=None):
                wait_time = random.randint(500, 1500) # generate random number (in second) for waiting time
                if timeout != None:
                    wait_time = timeout
                print(f"Waiting for {wait_time/1000} seconds for {description}...")
                await page.wait_for_timeout(wait_time)
            
            max_scroll_attempts = 50
            scroll_attempts = 0

            await prevent_upward_scroll(page)
            while scroll_attempts < max_scroll_attempts:
                start_time = time.time()
                request_detected = False
                retry_count = 0
                max_retries = 4

                while not request_detected and retry_count < max_retries:
                    try:
                        if scroll_attempts == 0 and retry_count == 0:
                            await perform_random_wait(page, 'Readiness list ticket data')

                        print(f"\nScroll attempt: {scroll_attempts + 1}, Retry: {retry_count + 1}")
                        print(f"Pressing end button...")
                        await press_end_button(page)
                        await perform_random_wait(page, 'API Response', timeout=1000*(retry_count+1))
                        
                        if request_detected:
                            await perform_random_wait(page, 'Calming Down after request detected', timeout=random.randint(2500, 4000))
                            break

                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"No request detected, retrying... ({retry_count}/{max_retries})")
                        
                    except Exception as e:
                        print(f"Warning during scroll attempt: {str(e)}")
                        break
                
                if scroll_attempts < 5 and retry_count == 4:
                    # Detect and click the 'Best Seats' button if it appears
                    await detect_and_click_button(page, xpath_selector='//span[@data-bdd="quick-picks-sort-button-best"]', description="Best Seats")
                    # Wait vip star row visible
                    await page.wait_for_selector('div[data-bdd="quick-pick-ticket-info"]', state='visible')

                if not request_detected:
                    print("No API request detected after maximum retries, stopping...")
                    break
                
                scroll_attempts += 1
                end_time = time.time()
                execution_time = await count_execution_time(start_time, end_time)
                print(f"Execution time for scroll atempt {scroll_attempts + 1} is {execution_time}.")
            
            all_ticket_data = await extract_ticket_data(page)
            await save_or_update_file(url, page, all_ticket_data, output_filename)
            await process_result_data(output_filename)

            result = await read_json_async(output_filename)
            seat_pick = result.get('seat_pick')

            print("Seat Pick (Sect): ", seat_pick['raw_section_title'])
            print("Seat Pick (Price): ", seat_pick['raw_price'])


            await perform_random_wait(page, 'Readiness seat list', timeout=random.randint(5000, 10000))

            await detect_and_click_button(page, xpath_selector=f"""//li[starts-with(@data-bdd, "quick-picks-list") and 
                    .//span[contains(text(), "{seat_pick['raw_section_title']}")] and 
                    .//button[contains(text(), "{seat_pick['raw_price']}")]]//button""", description="Seat Pick")
            
            await perform_random_wait(page, 'Readiness checkout button', timeout=random.randint(5000, 10000))
            await detect_and_click_button(page, xpath_selector='//button[@data-bdd="offer-card-buy-button"]', description="Next Button go to Checkout")
            
            # Wait for the "Confirming Availability" overlay to appear ---
            await page.wait_for_selector("[data-bdd='polling-text']", state="visible")

            # Wait for the "Confirming Availability" overlay to disappear (auto-redirect) ---
            await page.wait_for_selector("[data-bdd='polling-text']", state="detached")

            # Wait for navigation to complete (wait for new title or content) ---
            await page.wait_for_load_state("load")

            await page.wait_for_timeout(10000)

            # --- Step 5: Verify page title is "Checkout" ---
            title = await page.title()
            if title == "Ticketmaster | Checkout":
                print("✅ Successfully reached Checkout page")
            else:
                print(f"❌ Unexpected title: {title}")

        except Exception as e:
            print(f"Error during scraping: {str(e)}")
        finally:
            await page.wait_for_timeout(20000)
            await browser.close()
