FROM python:3.12-slim

WORKDIR /app

# Copy only requirements first to leverage Docker layer caching
COPY requirements.txt ./requirements.txt

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]