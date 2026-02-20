FROM python:3.11-slim

WORKDIR /app

# Sistem paketlarini o'rnatish
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python paketlarini o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kodni nusxalash
COPY . .

# Data papkasini yaratish
RUN mkdir -p /data && chmod 777 /data

# Botni ishga tushirish
CMD ["python", "main.py"]