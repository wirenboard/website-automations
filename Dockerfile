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
COPY requirements.txt /app/

# Установка Python-зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Установка SSH-клиента
RUN apt-get update && apt-get install -y openssh-client \
    && mkdir -p ~/.ssh && chmod 0700 ~/.ssh

# Команда запуска по умолчанию
CMD ["bash"]
