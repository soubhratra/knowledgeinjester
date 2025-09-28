# Use a slim Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install full build toolchain and system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        make \
        python3-dev \
        libffi-dev \
        libssl-dev \
        libstdc++6 \
        libc++1 \
        libc++abi1 \
    && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy the entire project codebase
COPY . .

# ✅ Run collectstatic during the build phase — this is critical on Northflank
# Set BUILD_MODE to disable file logging during build
ENV BUILD_MODE=true
RUN python manage.py collectstatic --noinput

# Create logs directory for runtime file logging
RUN mkdir -p /app/logs

# Reset environment for runtime (enable file logging)
ENV BUILD_MODE=false
ENV RUNTIME_MODE=true

# Start the application server
CMD ["sh", "-c", "python startup.py && uvicorn knowledgeinjester.asgi:application --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips=*"]