FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application
COPY . .

# Copy the logger from parent directory
COPY ../logger.py .

# Expose port (if needed for health checks)
EXPOSE 8000

# Run the MCP server
CMD ["python", "main.py"]
