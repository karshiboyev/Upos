# Python bazasi
FROM python:3.12-slim

# Workdir yaratamiz
WORKDIR /app

# System kutubxonalarini o‘rnatamiz (psycopg2 va boshqalar uchun)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt ni ko‘chirib o‘tkazamiz
COPY requirements.txt .

# Kutubxonalarni o‘rnatamiz
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini ko‘chirib o‘tkazamiz
COPY . .

# Django static fayllarni yig‘amiz
RUN python manage.py collectstatic --noinput

# Default komanda (gunicorn orqali ishlatamiz)
CMD ["gunicorn", "root.wsgi:application", "--bind", "0.0.0.0:8000"]
