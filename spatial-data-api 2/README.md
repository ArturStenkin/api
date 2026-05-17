# Spatial Data API

Web-приложение для загрузки и обработки пространственных данных в формате Shapefile.

## Используемые технологии

- FastAPI
- Jinja2
- Bootstrap 5
- pyshp

## Возможности

- Загрузка ZIP-архива
- Распаковка shapefile
- Чтение пространственных данных
- Преобразование в GeoJSON
- Просмотр результата
- Swagger UI FastAPI

---

# 1. Создание виртуального окружения

## Windows

```bash
python -m venv venv
venv\Scripts\activate
```

## Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

---

# 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

---

# 3. Запуск проекта

```bash
uvicorn app.main:app --reload
```

После запуска приложение будет доступно:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

# 4. Загрузка проекта на GitHub

## Инициализация Git

```bash
git init
```

## Добавление файлов

```bash
git add .
```

## Коммит

```bash
git commit -m "Initial commit"
```

## Подключение репозитория

```bash
git remote add origin https://github.com/USERNAME/REPOSITORY.git
```

## Отправка проекта

```bash
git push -u origin main
```

---

# 5. Деплой на Render

## Шаги

1. Загрузить проект на GitHub
2. Перейти на сайт Render
3. Создать новый Web Service
4. Подключить GitHub-репозиторий
5. Render автоматически обнаружит render.yaml
6. Нажать Deploy

---

# Важно

Проект НЕ использует:

- GDAL
- GeoPandas
- Shapely
- Fiona

Поэтому приложение успешно деплоится на Render без ошибок сборки.
