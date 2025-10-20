FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*


# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 ui_user && \
    chown -R ui_user:ui_user /app
USER ui_user

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 5000

# Set default command
CMD ["python", "app/app.py"]