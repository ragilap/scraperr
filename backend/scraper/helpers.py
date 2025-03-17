from datetime import datetime
import json
import re
import aiofiles
from natsort import natsorted

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

async def click_button_strict(page, xpath_selector=None, description=None, optional=False,  timeout=20000,index=None):
    try:
        if xpath_selector:
            await page.wait_for_selector(xpath_selector, state='visible', timeout=timeout)
            
            elements = page.locator(xpath_selector)
            count = await elements.count()

            if count == 0:
                raise ValueError(f"{description} Not Detected, Stopping...")
            elif count == 1 or index is None:
                await elements.first.click()
                print(f"{description} Detected and Clicked")
            elif index is not None and 0 <= index < count:
                await elements.nth(index).click()
                print(f"{description} (Element #{index}) Detected and Clicked")
            else:
                raise IndexError(f"Invalid index {index}. Only {count} elements found.")
        else:
            raise ValueError(f"{description} Not Detected, Stopping...")

    except Exception as e:
        if optional:
            print(f"{description} Not Detected, Continuing... Error: {e}")
        else:
            raise ValueError(f"{description} Not Detected, Stopping... Error: {e}")
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