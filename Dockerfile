FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD gunicorn app:app --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 2 --timeout 120
```

**2. requirements.txt 수정:**
```
flask==3.0.0
gunicorn==21.2.0
requests==2.31.0
beautifulsoup4==4.12.2
