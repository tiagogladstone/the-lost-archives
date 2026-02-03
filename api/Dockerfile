# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY ./requirements.txt /app/

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . /app/

# Make port 8080 available to the world outside this container
# Cloud Run expects the container to listen on the port defined by the PORT env var.
# Uvicorn by default listens on 8000, so we'll use that and let Cloud Run map it.
EXPOSE 8080

# Run main.py when the container launches
# Use the PORT environment variable provided by Cloud Run, default to 8080 for local testing.
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
