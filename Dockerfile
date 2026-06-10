FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source files (filtered by .dockerignore)
COPY . /app/

# Set default entrypoint
ENTRYPOINT ["python", "main.py"]
