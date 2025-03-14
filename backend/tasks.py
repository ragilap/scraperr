import asyncio
from celery import Celery
from pymongo import MongoClient
from scraper.scraper import scrape_with_session
from pathlib import Path

# Redis setup
redis_url = "redis://:RedisYefta123!@localhost:6379/0"

# MongoDB setup
mongodb_uri = "mongodb://localhost:27017/yefta-db"

client = MongoClient(mongodb_uri)
db = client["yefta-db"]
collection = db["inventory"]

# Celery setup
celery = Celery('scraping', broker=redis_url, backend=mongodb_uri)
celery.conf.update(
    worker_pool='prefork',
    # worker_concurrency=4
)

# Celery Task for Scraping
@celery.task(bind=True)
def scrape_task(self, url: str, output_filename: str):
    # Run the async scraping function
    result = asyncio.run(scrape_website(url, output_filename))
    return result

async def scrape_website(url: str, output_filename: str):
    try:
        # Use Playwright async API
        result_json_path = Path(__file__).parent / "result" / output_filename
        await scrape_with_session(url=url, output_filename=str(result_json_path))

        # Save the scraped content to MongoDB
        collection.update_one(
            { "url": url },
            { 
                "$set" : { 
                    "status": "success" 
                }
            }
        )

        return {
            "url": url,
            "status": "success",
            "result_file": output_filename
        }

    except Exception as e:
        # Handle scraping errors and save error status in MongoDB
        collection.update_one(
            { "url": url },
            {
                "$set" : {
                    "status": "failed",
                    "error": str(e)
                }
            }
        )
        
        return {
            "url": url,
            "status": "failed",
            "error": str(e)
        }
