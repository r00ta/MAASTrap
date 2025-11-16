FROM python:3.11-slim

WORKDIR /app

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
