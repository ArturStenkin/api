# Система загрузки пространственных данных

Web-приложение для курсовой работы на тему: «Разработка webAPI для пакетной загрузки файлов, содержащих пространственные данные».

Проект поддерживает загрузку:

- одного ZIP-архива с файлами Shapefile;
- набора отдельных файлов Shapefile: `.shp`, `.shx`, `.dbf`, `.prj`, `.cpg`.

В проекте не используются GeoPandas, GDAL, Fiona и Shapely. Для чтения Shapefile применяется легкая библиотека `pyshp`, поэтому приложение стабильно деплоится на Render.

## Технологии

| Компонент | Описание |
| --- | --- |
| Python | Язык программирования для реализации серверной логики |
| FastAPI | Веб-фреймворк для построения API |
| pyshp | Библиотека для чтения файлов Shapefile без GDAL |
| Bootstrap 5 | Адаптивный интерфейс приложения |

## Структура

```text
spatial-data-api-full/
├── app/
│   ├── main.py
│   └── temp/
├── requirements.txt
├── README.md
├── .gitignore
└── render.yaml
```

## Локальный запуск

Создайте виртуальное окружение:

```bash
python -m venv venv
```

Активируйте окружение.

macOS / Linux:

```bash
source venv/bin/activate
```

Windows PowerShell:

```powershell
venv\Scripts\Activate.ps1
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

Запустите приложение:

```bash
uvicorn app.main:app --reload
```

Откройте:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

## Использование

На главной странице можно выбрать:

- один ZIP-файл, внутри которого есть `.shp`;
- несколько отдельных файлов Shapefile, например `data.shp`, `data.shx`, `data.dbf`, `data.prj`.

После загрузки приложение:

- сохраняет файлы во временную папку `app/temp`;
- распаковывает ZIP, если загружен архив;
- находит файл `.shp`;
- читает данные через `pyshp`;
- преобразует объекты в GeoJSON;
- показывает имя файла, статус, количество объектов и первые 2 объекта GeoJSON.

## Загрузка на GitHub

Создайте новый репозиторий на GitHub и загрузите в него содержимое папки `spatial-data-api-full`.

Файлы должны лежать в корне репозитория:

```text
app/
requirements.txt
render.yaml
README.md
.gitignore
```

## Деплой на Render

При создании Web Service на Render используйте:

**Build Command**

```bash
pip install -r requirements.txt
```

**Start Command**

```bash
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
```

Если используете файл `render.yaml`, Render возьмет эти команды автоматически.

Важно: поле Root Directory оставьте пустым, если файлы проекта лежат в корне репозитория.
