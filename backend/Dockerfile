# Backend Dockerfile (backend/Dockerfile)

# Use the official Python image as a base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install system dependencies required for Playwright and other necessary tools
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libgdk-pixbuf2.0-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libpangocairo-1.0-0 \
    libvulkan1 \
    lsb-release \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY ./backend/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install the browsers needed by Playwright
RUN python -m playwright install

# Copy the rest of the application code
COPY ./backend /app

# Expose the port for FastAPI
EXPOSE 8000

# Set environment variables (MongoDB and Redis credentials)
ENV MONGO_URI=mongodb://yefta:MongoYefta123!@localhost:27017/yefta-db
ENV REDIS_HOST=yefta_redis
ENV REDIS_PASSWORD=RedisYefta123!

# Run FastAPI app with Uvicorn
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 & celery -A tasks worker --loglevel=INFO"]
