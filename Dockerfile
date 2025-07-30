FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Build frontend if it exists
RUN if [ -d "frontend" ]; then \
        cd frontend && \
        npm install && \
        npm run build && \
        cd ..; \
    fi

# Make startup script executable
RUN chmod +x start.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Railway will set the PORT environment variable
# No need to EXPOSE a specific port

# Run the application using the startup script
CMD ["./start.sh"]