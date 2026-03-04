FROM python:3.11-slim

# Install system dependencies for OpenCV and core operations
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files (filtered by .dockerignore)
COPY . /app/


# Set default entrypoint
ENTRYPOINT ["python", "main.py"]
