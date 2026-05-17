# ============================================================
# Курсовая работа: WebAPI для пакетной загрузки пространственных данных
# Технологии: Python 3, FastAPI, GeoPandas, Jinja2, Bootstrap 5
# ============================================================

import os
import zipfile
import shutil
import json
import uuid
from pathlib import Path

import geopandas as gpd
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ─── Инициализация приложения ───────────────────────────────
app = FastAPI(
    title="WebAPI для загрузки пространственных данных",
    description="Курсовая работа: пакетная загрузка и обработка пространственных данных (Shapefile → GeoJSON)",
    version="1.0.0",
    contact={"name": "Студент", "email": "student@example.com"},
)

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent

# Директория для временных файлов (распакованные архивы)
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Подключение статических файлов (CSS, JS и т.д.)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Подключение шаблонизатора Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ─── Утилиты ────────────────────────────────────────────────

def cleanup_temp(folder: Path):
    """Удаляет временную директорию после обработки."""
    if folder.exists():
        shutil.rmtree(folder, ignore_errors=True)


def find_shapefile(directory: Path):
    """
    Рекурсивно ищет первый .shp файл в указанной директории.
    Возвращает путь к файлу или None, если файл не найден.
    """
    for path in directory.rglob("*.shp"):
        return path
    return None


def process_shapefile(shp_path: Path) -> dict:
    """
    Читает Shapefile через GeoPandas и конвертирует в GeoJSON.

    Возвращает словарь с:
    - filename: имя файла
    - status: статус обработки
    - feature_count: количество объектов
    - preview: первые 2 объекта GeoJSON
    - geojson: полный GeoJSON (строка)
    """
    # Чтение Shapefile через GeoPandas
    gdf = gpd.read_file(shp_path)

    # Нормализация системы координат в WGS84 (EPSG:4326) для совместимости
    if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # Конвертация всего датафрейма в GeoJSON
    geojson_str = gdf.to_json(ensure_ascii=False)
    geojson_data = json.loads(geojson_str)

    # Превью — первые 2 объекта для отображения на странице
    preview_features = geojson_data.get("features", [])[:2]
    preview = json.dumps({"type": "FeatureCollection", "features": preview_features},
                         ensure_ascii=False, indent=2)

    return {
        "filename": shp_path.name,
        "status": "Успешно обработан",
        "feature_count": len(gdf),
        "crs": str(gdf.crs) if gdf.crs else "Не определена",
        "preview": preview,
        "geojson": geojson_str,
    }


# ─── Маршруты (Routes) ──────────────────────────────────────

@app.get("/", response_class=HTMLResponse, summary="Главная страница")
async def index(request: Request):
    """
    GET /
    Возвращает главную HTML-страницу с формой загрузки файла.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload", summary="Загрузка и обработка ZIP-архива")
async def upload_file(request: Request, file: UploadFile = File(...)):
    """
    POST /upload

    Принимает ZIP-архив, содержащий Shapefile.
    Распаковывает архив, находит .shp файл,
    читает его через GeoPandas и возвращает GeoJSON.

    - **file**: ZIP-архив со Shapefile (.shp, .dbf, .shx и т.д.)
    """

    # Создаём уникальную временную папку для этого запроса
    session_id = uuid.uuid4().hex
    temp_folder = TEMP_DIR / session_id
    temp_folder.mkdir(parents=True, exist_ok=True)

    try:
        # ── 1. Проверяем расширение файла ──────────────────
        original_name = file.filename or ""
        if not original_name.lower().endswith(".zip"):
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": f"Ошибка: файл «{original_name}» не является ZIP-архивом. "
                         "Пожалуйста, загрузите файл с расширением .zip"
            })

        # ── 2. Сохраняем загруженный файл на диск ──────────
        zip_path = temp_folder / original_name
        content = await file.read()
        zip_path.write_bytes(content)

        # ── 3. Проверяем целостность ZIP-архива ────────────
        if not zipfile.is_zipfile(zip_path):
            cleanup_temp(temp_folder)
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": "Ошибка: архив повреждён или имеет неверный формат ZIP."
            })

        # ── 4. Распаковываем архив ─────────────────────────
        extract_dir = temp_folder / "extracted"
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_dir)

        # ── 5. Ищем Shapefile (.shp) ───────────────────────
        shp_path = find_shapefile(extract_dir)
        if shp_path is None:
            cleanup_temp(temp_folder)
            return templates.TemplateResponse("index.html", {
                "request": request,
                "error": "Ошибка: в архиве не найден файл Shapefile (.shp). "
                         "Убедитесь, что архив содержит файлы .shp, .dbf, .shx."
            })

        # ── 6. Читаем и конвертируем Shapefile ────────────
        result = process_shapefile(shp_path)

        # ── 7. Очищаем временные файлы ─────────────────────
        cleanup_temp(temp_folder)

        # ── 8. Возвращаем страницу с результатом ──────────
        return templates.TemplateResponse("index.html", {
            "request": request,
            "result": result,
        })

    except Exception as e:
        cleanup_temp(temp_folder)
        return templates.TemplateResponse("index.html", {
            "request": request,
            "error": f"Ошибка при обработке файла: {str(e)}"
        })


@app.get("/api/info", summary="Информация об API")
async def api_info():
    """
    GET /api/info
    Возвращает информацию о версии и возможностях API.
    """
    return JSONResponse({
        "name": "WebAPI для загрузки пространственных данных",
        "version": "1.0.0",
        "description": "Курсовая работа: пакетная загрузка и обработка пространственных данных",
        "supported_formats": ["ZIP-архив со Shapefile (.shp, .dbf, .shx)"],
        "output_format": "GeoJSON (EPSG:4326)",
        "endpoints": {
            "GET /": "Главная страница (веб-интерфейс)",
            "POST /upload": "Загрузка и обработка ZIP-архива",
            "GET /api/info": "Информация об API",
            "GET /docs": "Swagger UI (интерактивная документация)",
            "GET /redoc": "ReDoc (документация)",
        }
    })
