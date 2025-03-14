import json
import aiofiles
import time
import asyncio
from .helpers import convert_date, write_json_async, process_section_info, process_price, count_execution_time
from collections import defaultdict

async def extract_ticket_data(page):
    start_time = time.time()  # Record the start time
    
    ticket_data = []
    row_items = page.locator('[data-bdd^="quick-picks-list-item-"]')
    max_length = await row_items.count()

    # Gather all async operations to be run in parallel
    tasks = []

    for i in range(max_length):
        tasks.append(extract_ticket_from_row(row_items, i))

    # Run all tasks concurrently
    ticket_data = await asyncio.gather(*tasks)

    end_time = time.time()  # Stop the record time
    execution_time = await count_execution_time(start_time, end_time)

    print(f"Successfully extracted {max_length} data in {execution_time}.")
    
    return {'ticket_data': ticket_data}

# Helper function to extract data from a single row
async def extract_ticket_from_row(row_items, index):
    row = row_items.nth(index)
    
    section, ticket_type, price = await asyncio.gather(
        row.locator('span').nth(0).text_content(timeout=0),
        row.locator('span').nth(1).text_content(timeout=0),
        row.locator('button').text_content(timeout=0)
    )
    
    return {
        'section': section.strip() if section else '',
        'ticket_type': ticket_type.strip() if ticket_type else '',
        'price': price.strip() if price else ''
    }

async def save_or_update_file(url, page, data, filename="ticket_data.json"):
    try:
        # Detect currency from URL
        currency = "CA $" if ".ca" in url else "$"
        
        # Load existing data once, outside of the ticket processing loop
        try:
            async with aiofiles.open(filename, mode='r') as file:
                # Load the JSON data from the file
                existing_data = json.loads(await file.read())
        except FileNotFoundError:
            # Create default structure for new file if it doesn't exist
            existing_data = {
                'url': url,
                'title': await page.locator('.sc-a9bee614-14.fBtImi').text_content(),
                'held_on': convert_date(await page.locator('.sc-a9bee614-16.hAkUvx').text_content()),
                'location': await page.locator('.sc-84febfde-0.hWhRZd').text_content(),
                'sections': {},
                'recommendations': {}
            }

        # Use defaultdict to handle section initialization automatically
        sections_data = defaultdict(lambda: {'currency': currency, 'rows': []})

        # Process the ticket data
        for ticket in data['ticket_data']:
            section, row = await process_section_info(ticket['section'])
            row = section if row == "" else row  # Fallback if row is empty
            price = await process_price(ticket['price'])
            
            row_to_add = {"row": row, "price": price}

            # Add row to the correct section in the defaultdict
            sections_data[section]['rows'].append(row_to_add)

        # Convert defaultdict back to regular dict to store in JSON
        existing_data['sections'] = dict(sections_data)

        # Count sections and rows
        section_count = len(existing_data['sections'])
        row_count = sum(len(section['rows']) for section in existing_data['sections'].values())

        # Add "count" key to the dictionary
        existing_data['count'] = {
            "section": section_count,
            "row": row_count
        }

        # Flatten all rows into a list with their section, row, and price
        all_recommendations = []
        for section_name, section_data in existing_data['sections'].items():
            for row in section_data['rows']:
                all_recommendations.append({
                    "section": section_name,
                    "row": row["row"],
                    "price": row["price"]
                })

        # Sort recommendations by price in ascending order
        sorted_recommendations = sorted(all_recommendations, key=lambda x: x["price"])

        # Generate new recommendation array in the desired format
        new_recommendations = [
            f"Section: {rec['section']}, Row: {rec['row']}, Harga: {currency} {rec['price']}" 
            for rec in sorted_recommendations[:8]
        ]

        # Update the event data with the new recommendation list
        existing_data["recommendations"] = new_recommendations
        
        # Write the updated data to the file asynchronously
        await write_json_async(filename, existing_data)
        print(f"Data has been updated on: {filename}.")
        return True
        
    except Exception as e:
        print(f"Error saving data: {str(e)}")
        return False
