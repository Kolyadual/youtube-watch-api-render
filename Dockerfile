FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    ffmpeg \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Копируем код приложения
COPY . .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем yt-dlp с необязательными зависимостями (brotli, certifi и т.д.)
# и плагин для обхода SABR/nsig защиты
RUN pip install --no-cache-dir "yt-dlp[default]" yt-dlp-ejs

EXPOSE 5000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--timeout", "300"]
