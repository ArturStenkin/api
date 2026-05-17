import os
import json
import shutil
import zipfile
from pathlib import Path

import shapefile
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# ---------------------------------------------------
# Инициализация FastAPI приложения
# ---------------------------------------------------

app = FastAPI(
    title="Spatial Data API",
    description="WebAPI для пакетной загрузки пространственных данных",
    version="1.0"
)

# ---------------------------------------------------
# Пути проекта
# ---------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"

# Создаем временную папку при запуске
TEMP_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------
# Настройка шаблонов
# ---------------------------------------------------

templates = Jinja2Templates(directory="app/templates")


# ---------------------------------------------------
# Главная страница
# ---------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "result": None
        }
    )


# ---------------------------------------------------
# Функция преобразования shapefile в GeoJSON
# ---------------------------------------------------

def shapefile_to_geojson(shp_path):
    """
    Преобразование shapefile в GeoJSON
    """

    reader = shapefile.Reader(str(shp_path))

    fields = [field[0] for field in reader.fields[1:]]

    features = []

    for sr in reader.shapeRecords():

        attributes = dict(zip(fields, sr.record))

        feature = {
            "type": "Feature",
            "geometry": sr.shape.__geo_interface__,
            "properties": attributes
        }

        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson


# ---------------------------------------------------
# Endpoint загрузки файла
# ---------------------------------------------------

@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):

    # Очистка временной папки
    shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(exist_ok=True)

    result = {
        "filename": file.filename,
        "status": "",
        "count": 0,
        "preview": [],
        "error": None
    }

    try:

        # Проверка ZIP
        if not file.filename.endswith(".zip"):
            result["error"] = "Ошибка: загруженный файл не является ZIP-архивом."
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "result": result}
            )

        # Сохранение ZIP
        zip_path = TEMP_DIR / file.filename

        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Распаковка ZIP
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(TEMP_DIR)

        except zipfile.BadZipFile:
            result["error"] = "Ошибка: ZIP-архив поврежден."
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "result": result}
            )

        # Поиск SHP файла
        shp_files = list(TEMP_DIR.rglob("*.shp"))

        if not shp_files:
            result["error"] = "Ошибка: файл .shp не найден."
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "result": result}
            )

        shp_path = shp_files[0]

        # Чтение shapefile
        try:
            geojson = shapefile_to_geojson(shp_path)

        except Exception:
            result["error"] = "Ошибка чтения shapefile."
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "result": result}
            )

        # Формирование результата
        result["status"] = "Файл успешно обработан"
        result["count"] = len(geojson["features"])
        result["preview"] = geojson["features"][:2]

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": result
            }
        )

    except Exception as e:

        result["error"] = f"Непредвиденная ошибка: {str(e)}"

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "result": result
            }
        )
