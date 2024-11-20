# Используем базовый образ Python
FROM python:3.10-slim

# Установка необходимых системных пакетов
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Установка рабочей директории
WORKDIR /app

# Копирование файлов проекта
COPY changed-habr-articles/ /app/

# Установка зависимостей (если есть requirements.txt)
# RUN pip install --no-cache-dir -r requirements.txt

# Команда запуска по умолчанию
CMD ["bash"]
