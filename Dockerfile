FROM python:3.11-slim

WORKDIR /app

# Install ISO generation and manipulation tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cloud-image-utils \
    genisoimage \
    xorriso \
    isolinux \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY auth.py .
COPY database.py .
COPY static/ static/

# Create directories for images and database
RUN mkdir -p images

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "app.py"]
