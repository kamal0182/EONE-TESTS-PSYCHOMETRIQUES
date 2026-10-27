FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py createcachetable && python manage.py seed_core_values_bank && python manage.py ensure_admin && gunicorn eone_test.wsgi:application --bind 0.0.0.0:8000 --workers 2"]
