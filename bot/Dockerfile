FROM python:3.12-slim

WORKDIR /app

# Ensure Python can import bare modules inside /app/bot (storage, service, utils, etc.)
ENV PYTHONPATH="/app/bot:${PYTHONPATH}"

# Copy only requirements first to leverage Docker layer caching (paths relative to build context)
COPY bot/requirements.txt ./requirements.txt

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code under /app/bot so that 'import bot.*' works
COPY bot/ /app/bot

# Start the app (module path includes package)
CMD ["uvicorn", "bot.main:app", "--host", "0.0.0.0", "--port", "8080"]