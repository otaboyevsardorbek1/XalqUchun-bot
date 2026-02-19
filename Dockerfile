FROM python:3.11-slim

WORKDIR /app

# Kutubxonalarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Barcha kodlarni nusxalash
COPY . .

# Volume mount qilingan papka
RUN mkdir -p /data && chmod 777 /data

# Botni ishga tushirish
CMD ["python", "main.py"]