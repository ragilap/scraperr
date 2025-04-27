# Frontend Dockerfile (frontend/Dockerfile)

# Use the latest official Node.js image as a base
FROM node:latest

# Set the working directory
WORKDIR /app

# Copy the rest of the application code
COPY ./frontend /app

# Install dependencies
COPY ./frontend/package.json ./frontend/package-lock.json ./
RUN npm install

# Build the Next.js app for production
RUN npm run build --verbose

# Expose the port the app will run on
EXPOSE 3000

# Start the Next.js app in production mode
CMD ["npm", "run", "start"]
