# Use the official Python image
FROM python:3.11-slim

# Install system dependencies for Tesseract and OpenCV
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Create necessary directories for persistence or temporary storage
# Create necessary directories for persistence
RUN mkdir -p instance/uploads/patients instance/uploads/records

# Expose the default port (Render will override this)
EXPOSE 5001

# Command to run the application using gunicorn with gevent websocket
# We use sh -c to allow the $PORT environment variable to be substituted
CMD ["sh", "-c", "gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app --bind 0.0.0.0:${PORT:-5001}"]
