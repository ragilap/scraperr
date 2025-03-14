from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from pydantic import BaseModel
from celery.result import AsyncResult
from pymongo import MongoClient
from datetime import datetime, timedelta
from tasks import scrape_task
import validators

# FastAPI app setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or list specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods, or specify e.g. ["GET", "POST"]
    allow_headers=["*"],  # Allow all headers
)

# Mount the 'result' directory to serve static files
result_path = Path(__file__).parent / "result"
app.mount("/api/result", StaticFiles(directory=result_path), name="result")

# MongoDB setup
mongodb_uri = "mongodb://localhost:27017/yefta-db"

client = MongoClient(mongodb_uri)
db = client["yefta-db"]
collection = db["inventory"]

class ScrapeRequest(BaseModel):
    url: str
    code: str

# Home Route (Welcome Page)
@app.get("/api/")
async def welcome():
    return {"message": "Welcome to the Web Scraping API"}

# Scrape URL Route
@app.post("/api/scrape")
async def scrape(scrape_request: ScrapeRequest):
    url = scrape_request.url
    code = scrape_request.code
    if code != "TRIAL":
        return {
            "status": "error",
            "message": f"Your code is invalid.",
        }
    
    # Check if the URL is already scraped or is in progres last 1 hours
    current_time = datetime.now()
    one_hour_ago = current_time - timedelta(hours=1)
    existing_data = collection.find_one({"url": url, "created_at": {"$gte": one_hour_ago}})
    if existing_data:
        if existing_data['status'] == "pending":
            return {
                "status": "pending",
                "message": f"URL {url} is in progress.",
                "task_id": existing_data['task_id']
            }
        if existing_data['status'] == "success":
            return {
                "status": "success",
                "message": f"URL {url} is already scraped.",
                "result_file": existing_data['result_file']
            }
    
    # Check if the URL is invalid format
    if not validators.url(url):
        return {
            "status": "error",
            "message": f"URL {url} is invalid.",
        }

    # Create file name with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"ticket_data_{timestamp}.json"

    # Start the scraping task using Celery
    task = scrape_task.apply_async(args=[url, output_filename])

    # Insert begin scraping task to MongoDB
    collection.insert_one({
        "task_id": task.id,
        "url": url,
        "status": "pending",
        "result_file": output_filename,
        "created_at": current_time
    })

    return {
        "status": "pending",
        "message": f"The request to scrape URL {url} is now being processed.",
        "task_id": task.id
    }

# Status Check Route
@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    existing_data = collection.find_one({"task_id": task_id})
    if not existing_data:
        return {
            "status": "error",
            "message": f"Task ID {task_id} is not found.",
        }
    task_result = AsyncResult(task_id)
    if task_result.state == 'PENDING':
        return {
            "status": "pending",
            "message": f"Task ID {task_id} is in progress.",
            "task_id": task_id
        }
    elif task_result.state == 'SUCCESS':
        return {
            "status": "scraped",
            "message": f"Task ID {task_id} is already scraped.",
            "task_id": task_id, 
            "result": task_result.result
        }
    elif task_result.state == 'FAILURE':
        return {
            "status": "error",
            "message": f"Failure during scraping task ID {task_id}.",
            "task_id": task_id
        }
    else:
        return {
            "status": task_result.state, 
            "task_id": task_id
        }
