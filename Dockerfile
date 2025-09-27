# Use a slim Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install build dependencies (required for madoka and other C extensions)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        make \
        python3-dev \
    && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the entire project codebase
COPY . .

# ✅ Run collectstatic during the build phase — this is critical on Northflank
RUN python manage.py collectstatic --noinput

# Start the application server
CMD ["sh", "-c", "python startup.py && uvicorn knowledgeinjester.asgi:application --host 0.0.0.0 --port 8000"]
