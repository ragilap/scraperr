import argparse
import asyncio
import time
from scraper import scrape_with_session
from helpers import count_execution_time

async def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description='Scrape Ticketmaster with Session Management')
    parser.add_argument('url', type=str, help='URL to scrape')
    args = parser.parse_args()
    await scrape_with_session(args.url.strip(), headless=False)

    end_time = time.time()
    execution_time = await count_execution_time(start_time, end_time)
    print(f"\nExecution time: {execution_time}.")

if __name__ == "__main__":
    asyncio.run(main())
