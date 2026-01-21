# backend/Dockerfile

FROM python:3.12-slim

# 1) Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 2) Set working directory in the container
WORKDIR /app

# 3) Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4) Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# 5) Copy project code
COPY . /app

# 6) Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
