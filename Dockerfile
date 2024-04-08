FROM python:3.11-slim

WORKDIR /deadline-web-app-backend

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libopenexr-dev \
    openexr \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "launcher.py"]