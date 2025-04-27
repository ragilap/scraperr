from datetime import datetime
import json
import time
import random
import re
import aiofiles
from natsort import natsorted
import asyncio

def convert_date(date_str):
    try:
        print(f"DEBUG: Raw date_str = '{date_str}'")  # Debugging

        # Tambahkan tahun jika tidak ada (default tahun sekarang)
        current_year = datetime.now().year
        if not re.search(r'\d{4}', date_str):  
            date_str += f", {current_year}"

        # Pastikan format waktu memiliki AM/PM
        if not re.search(r'\b(AM|PM)\b', date_str):
            date_str += " PM"  # Asumsi default ke PM

        print(f"DEBUG: After fixing format = '{date_str}'")  # Debugging

        # Coba parsing dengan beberapa format yang mungkin
        formats = [
            "%a • %b %d • %I:%M %p, %Y",
            "%A • %b %d • %I:%M %p, %Y",
            "%a • %b %d • %I:%M %p"
        ]
        date_obj = None
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                break  # Berhenti kalau berhasil
            except ValueError:
                continue

        if not date_obj:
            raise ValueError("Format tidak cocok dengan yang diharapkan")

    except ValueError as e:
        print(f"ERROR: Failed to parse '{date_str}' -> {e}")
        return None  # Bisa diganti dengan string error

    # Mapping hari dan bulan ke bahasa Indonesia
    weekday_map = {
        "Mon": "Senin", "Tue": "Selasa", "Wed": "Rabu", "Thu": "Kamis", "Fri": "Jumat", "Sat": "Sabtu", "Sun": "Minggu"
    }
    month_map = {
        "Jan": "Januari", "Feb": "Februari", "Mar": "Maret", "Apr": "April", "May": "Mei", "Jun": "Juni", 
        "Jul": "Juli", "Aug": "Agustus", "Sep": "September", "Oct": "Oktober", "Nov": "November", "Dec": "Desember"
    }

    formatted_date = f"{weekday_map[date_obj.strftime('%a')]}, {date_obj.day} {month_map[date_obj.strftime('%b')]}, {date_obj.year}, {date_obj.strftime('%H:%M')}"
    return formatted_date

async def detect_and_click_button(page, xpath_selector=None, description=None, optional=False, timeout=20000):
    try:
        if xpath_selector:
            await page.wait_for_selector(xpath_selector, state='visible', timeout=timeout)
            await page.locator(xpath_selector).click()
            print(f"{description} Detected and Clicked")
        else:
            raise ValueError(f"{description} Not Detected, Stopping...")
    except:
        if optional:
            print(f"{description} Not Detected, Continuing...")
        else:
            raise ValueError(f"{description} Not Detected, Stopping...")

async def click_button_strict(page, xpath_selector, description="Button", index=0, timeout=10000):
    """Klik tombol berdasarkan XPath dengan dukungan index jika ada lebih dari satu tombol."""
    try:
        print(f"Trying to click '{description}' button...")

        await page.wait_for_selector(xpath_selector, timeout=timeout)

        buttons = await page.locator(xpath_selector).all()

        if len(buttons) > 0:
            print(f"Ditemukan {len(buttons)} tombol, mencoba klik tombol dengan index {index}...")

            if index < len(buttons):
                await buttons[index].click()
                print(f"Berhasil mengklik '{description}' button dengan index {index}!")
            else:
                print(f"Index {index} melebihi jumlah tombol yang ditemukan ({len(buttons)}), menggunakan tombol pertama.")
                await buttons[0].click()
        else:
            print(f"Tombol '{description}' tidak ditemukan!")

    except Exception as e:
        print(f"Error saat mengklik '{description}': {e}")

async def detect_and_click_aria_disable(page, xpath_selector: str, description: str, timeout: int = 15000):
    print(f"Looking for {description} button...")
    # Tunggu tombol kelihatan dulu
    await page.wait_for_selector(xpath_selector, state="visible", timeout=timeout)
    
    button = page.locator(xpath_selector)

    try:
        await button.click(force=True)
        print(f"Clicked {description} button!")
    except Exception as e:
        print(f"Click failed: {e}")
        raise Exception(f"Failed to click {description} button")

async def custom_human_scroll(page,selector):
    """Scroll ke bawah secara bertahap seperti manusia hingga mencapai akhir halaman."""
    scroll_attempts = random.randint(3, 6)
    scroll_pause_time = random.uniform(0.5, 1.5)

    element = await page.query_selector(selector)
    if not element:
        print(f"Element with selector '{selector}' not found.")
        return

    for attempt in range(scroll_attempts):
        scroll_distance = random.randint(200, 600)

        print(f"[Scroll Attempt {attempt+1}] Scrolling down {scroll_distance} pixels...")
        await page.evaluate(f'''
            (element) => {{
                element.scrollBy(0, {scroll_distance});
            }}
        ''', element)
        await asyncio.sleep(scroll_pause_time)  # Jeda seperti manusia

    print("[Human Scroll] Scrolling finished!")

async def handler_queue(page, timeout_initial=10000, ):
    print("Checking queue status...")

    try:
        test = 'h3[data-bdd="statusСard-heading"]'
        await page.wait_for_selector(test, state="visible", timeout=timeout_initial)
        hello = await page.inner_text(test)
        print(hello)
        queue_status_locator = 'h2[data-bdd="statusСard-peopleInLine-count"]'
        await page.wait_for_selector(queue_status_locator, state="visible", timeout=40000)  

        status_text = await page.inner_text(queue_status_locator)
        print(f"Initial Queue Status: {status_text}")

        while True:
            if "It's your turn" in status_text:
                print("It's your turn! Proceeding to next step with a 20-30 second delay.")
                await page.wait_for_timeout(20000)  
                break

            if "calculating" not in status_text and "It's your turn" not in status_text:
                print(f"Queue status updated: {status_text}. Proceeding to next...")

                people_ahead = int(status_text.split()[0])  
                if people_ahead > 100:
                    await page.wait_for_timeout(15000) 
                else:
                    await page.wait_for_timeout(5000)  

            print("Still in queue... Checking again in 5 seconds.")
            await page.wait_for_timeout(5000)  
            status_text = await page.inner_text(queue_status_locator)
            print(f"Updated Queue Status: {status_text}")

    except Exception as e:
        print(f"Error while waiting for queue status: {e}")
        return False

    return True




async def ensure_element_visible(page, xpath_selector, timeout=30000):
    try:
        await page.wait_for_selector(xpath_selector, state='visible', timeout=timeout)
        print("Element is visible.")
    except:
        print("Element not visible within the timeout.")

# Function to extract and print the desired data
async def print_section_data(section_name, section_data, currency):
    # Extract prices and rows
    prices = sorted(set(f"{currency}{row['price']}" for row in section_data))
    rows = sorted(set(row['row'] for row in section_data))

    # Calculate price range (handling the currency in the range)
    min_price = min(section_data, key=lambda x: x['price'])
    max_price = max(section_data, key=lambda x: x['price'])
    price_range = f"{currency}{min_price['price']} - {currency}{max_price['price']}"

    # Print section information
    print(f"Section {section_name}:")
    print(f"\tUnique Prices: {', '.join(prices)}")
    print(f"\tUnique Rows: {', '.join(rows)}")
    print(f"\tPrice Range: {price_range}")
    print(f"\tRow Count: {len(rows)}")

# Asynchronous function to read JSON file and process the data
async def process_result_data(filename):
    print("Generating result data...\n\n")
    try:
        # Open the file asynchronously using aiofiles
        async with aiofiles.open(filename, mode='r') as file:
            # Load the JSON data from the file
            data = json.loads(await file.read())
            updated_data = await remove_duplicate_rows(data)

            # Check if the data has the 'sections' key
            if 'sections' in updated_data:
                # Sort section names before processing
                sorted_section_names = natsorted(updated_data['sections'].keys())

                # Sort the sections by their keys
                updated_data['sections'] = {key: updated_data['sections'][key] for key in sorted_section_names}

                # Sort rows inside each section by price
                for section_data in updated_data['sections'].values():
                    section_data['rows'].sort(key=lambda x: x['price'])
                
                # Save sorted data to JSON file
                await write_json_async(filename, updated_data)

                # Iterate over the sorted section names and print the data
                for section_name in sorted_section_names:
                    section_data = updated_data['sections'][section_name]
                    currency = section_data['currency']  # Get the currency for this section
                    await print_section_data(section_name, section_data['rows'], currency)
            else:
                print("No section data found in the JSON file.")
    except FileNotFoundError:
        print(f"The file {filename} was not found.")
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from the file {filename}. Please check the file's format.")

# Async function to remove duplicates
async def remove_duplicate_rows(data):
    # Iterate over each section's data in sections
    for section_data in data['sections'].values():  # Changed to .values() to avoid using section key
        seen_rows = set()
        unique_rows = []

        # Iterate through the rows of each section
        for row_data in section_data['rows']:
            row_price = (row_data['row'], row_data['price'])  # Create a tuple of row and price

            # Check if this (row, price) combination has been seen before
            if row_price not in seen_rows:
                # Add to seen rows and keep the row
                seen_rows.add(row_price)
                unique_rows.append(row_data)

        # Update the section with the unique rows
        section_data['rows'] = unique_rows

    return data

# Async function to read the file
async def read_json_async(filename):
    async with aiofiles.open(filename, 'r', encoding='utf-8') as f:
        return json.loads(await f.read())

# Asynchronous function to write data to the JSON file
async def write_json_async(filename, data):
    try:
        # Open the file asynchronously using aiofiles
        async with aiofiles.open(filename, 'w', encoding='utf-8') as f:
            # Use json.dump to write the data to the file
            await f.write(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error writing to file {filename}: {e}")

# Helper function to process section and row info
async def process_section_info(section_text):
    # Expected format: "Sec 126 • Row 4"
    parts = section_text.split('•')
    if len(parts) == 2:
        section = parts[0].strip().replace('Sec ', '')
        row = parts[1].strip().replace('Row ', '')
        return section, row
    return section_text, ''

# Helper function to process price
async def process_price(price_text):
    price = price_text.replace('CA $', '').replace('CA', '').replace('$', '').replace(',', '').strip()
    try:
        return float(price)
    except ValueError as e:
        print(f"Error converting price: {price_text} -> {price}")
        raise e

async def count_execution_time(start_time, end_time):
    # Calculate execution time in seconds
    execution_time = end_time - start_time
    # Convert to minutes and seconds
    minutes = execution_time // 60
    seconds = execution_time % 60
    return f"{int(minutes)} minutes and {seconds:.2f} seconds"