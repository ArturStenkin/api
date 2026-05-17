# 🗺️ WebAPI для пакетной загрузки пространственных данных

**Курсовая работа** — разработка WebAPI для пакетной загрузки файлов, содержащих пространственные данные.

## 🛠️ Стек технологий

| Компонент | Технология |
|-----------|------------|
| Язык программирования | Python 3.11+ |
| Web-фреймворк | FastAPI |
| Шаблонизатор | Jinja2 |
| CSS-фреймворк | Bootstrap 5 |
| Обработка геоданных | GeoPandas |
| ASGI-сервер | Uvicorn |

## 📁 Структура проекта

```
spatial-data-api/
│
├── app/
│   ├── main.py              # Главный модуль FastAPI
│   ├── templates/
│   │   └── index.html       # Шаблон главной страницы (Jinja2 + Bootstrap 5)
│   ├── static/              # Статические файлы (CSS, JS, изображения)
│   └── temp/                # Временные файлы (создаётся автоматически)
│
├── requirements.txt         # Зависимости Python
├── README.md                # Документация проекта
├── .gitignore               # Исключения Git
└── render.yaml              # Конфигурация деплоя на Render
```

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/<ваш-логин>/spatial-data-api.git
cd spatial-data-api
```

### 2. Создание виртуального окружения

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

> ⚠️ GeoPandas требует системных библиотек (GDAL, GEOS). Если установка завершается с ошибкой, рекомендуется использовать [conda](https://docs.conda.io/):
> ```bash
> conda install geopandas
> ```

### 4. Запуск приложения

```bash
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу: **http://127.0.0.1:8000**

### 5. Запуск в VS Code

1. Откройте папку `spatial-data-api` в VS Code.
2. Выберите интерпретатор Python из виртуального окружения (`venv`).
3. Откройте встроенный терминал (`Ctrl+~`) и выполните:
   ```bash
   uvicorn app.main:app --reload
   ```

## 📡 Endpoints API

| Метод | URL | Описание |
|-------|-----|----------|
| `GET` | `/` | Главная страница с веб-интерфейсом |
| `POST` | `/upload` | Загрузка и обработка ZIP-архива со Shapefile |
| `GET` | `/api/info` | Информация об API в формате JSON |
| `GET` | `/docs` | Интерактивная документация Swagger UI |
| `GET` | `/redoc` | Документация ReDoc |

## 📦 Формат входных данных

Приложение принимает **ZIP-архив**, который должен содержать файлы Shapefile:

| Файл | Описание | Обязателен |
|------|----------|------------|
| `.shp` | Геометрия объектов | ✅ Да |
| `.dbf` | Атрибуты объектов | ✅ Да |
| `.shx` | Пространственный индекс | ✅ Да |
| `.prj` | Система координат | ⬜ Нет |

## 📤 Формат выходных данных

Результат обработки — **GeoJSON** (стандарт RFC 7946), система координат **WGS 84 (EPSG:4326)**.

## 📤 Загрузка на GitHub

```bash
# Инициализация репозитория (если не клонировали)
git init
git add .
git commit -m "Initial commit: WebAPI для пространственных данных"

# Публикация на GitHub
git remote add origin https://github.com/<ваш-логин>/spatial-data-api.git
git branch -M main
git push -u origin main
```

## ☁️ Деплой на Render

1. Зайдите на [render.com](https://render.com) и создайте аккаунт.
2. Нажмите **New → Web Service**.
3. Подключите репозиторий GitHub.
4. Render автоматически обнаружит `render.yaml` и применит настройки.
5. Нажмите **Deploy** — приложение будет доступно по публичному URL.

**Конфигурация `render.yaml`:**
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`

## 🧪 Тестирование

Для тестирования можно создать тестовый Shapefile и упаковать его в ZIP:

```python
import geopandas as gpd
import zipfile
from shapely.geometry import Point

# Создание простого GeoDataFrame
gdf = gpd.GeoDataFrame(
    {"name": ["Точка А", "Точка Б"]},
    geometry=[Point(37.6, 55.75), Point(30.3, 59.95)],
    crs="EPSG:4326"
)
gdf.to_file("test.shp")

# Упаковка в ZIP
with zipfile.ZipFile("test.zip", "w") as zf:
    for ext in ["shp", "dbf", "shx", "prj", "cpg"]:
        try:
            zf.write(f"test.{ext}")
        except FileNotFoundError:
            pass
```

## 📋 Описание логики обработки

```
ZIP-архив
    │
    ▼
Проверка формата файла (.zip)
    │
    ▼
Распаковка во временную директорию
    │
    ▼
Поиск файла .shp (рекурсивно)
    │
    ▼
Чтение Shapefile через GeoPandas
    │
    ▼
Перепроецирование в WGS84 (EPSG:4326)
    │
    ▼
Конвертация в GeoJSON
    │
    ▼
Отображение результата + очистка временных файлов
```

## 👤 Автор

Курсовая работа по дисциплине «Веб-программирование» / «ГИС-технологии»  
Студент группы: ________  
Преподаватель: ________  
