import json
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

import shapefile
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


# Пути проекта. Папка temp используется только для временной обработки загрузок.
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Spatial Data API",
    description="WebAPI для загрузки ZIP-архивов и файлов Shapefile",
    version="1.0.0",
)

templates = Jinja2Templates(directory=BASE_DIR / "templates")


ALLOWED_DIRECT_EXTENSIONS = {".shp", ".shx", ".dbf", ".prj", ".cpg"}


def make_result(
    filename: str = "",
    status: str = "",
    objects_count: int = 0,
    features: list[dict[str, Any]] | None = None,
    error: str = "",
) -> dict[str, Any]:
    """Создает единый объект результата для HTML-страницы."""
    first_features = features or []
    return {
        "filename": filename,
        "status": status,
        "objects_count": objects_count,
        "features": first_features,
        "features_json": json.dumps(first_features, ensure_ascii=False, indent=2, default=str),
        "error": error,
    }


def safe_filename(filename: str) -> str:
    """Оставляет только имя файла, чтобы архив не мог записать данные вне temp."""
    return Path(filename).name


def shape_to_geometry(shape: shapefile.Shape) -> dict[str, Any] | None:
    """Преобразует геометрию pyshp в GeoJSON geometry."""
    geo_interface = shape.__geo_interface__

    if geo_interface.get("type") == "Null":
        return None

    return {
        "type": geo_interface.get("type"),
        "coordinates": geo_interface.get("coordinates"),
    }


def read_shapefile(shp_path: Path) -> dict[str, Any]:
    """Читает Shapefile через pyshp и возвращает GeoJSON FeatureCollection."""
    try:
        reader = shapefile.Reader(str(shp_path), encoding="utf-8")
    except UnicodeDecodeError:
        # Частая ситуация для русскоязычных DBF-файлов.
        reader = shapefile.Reader(str(shp_path), encoding="cp1251")
    except Exception as exc:
        raise ValueError(f"Ошибка чтения Shapefile: {exc}") from exc

    try:
        fields = [field[0] for field in reader.fields[1:]]
        features = []

        for shape_record in reader.iterShapeRecords():
            geometry = shape_to_geometry(shape_record.shape)
            if geometry is None:
                continue

            properties = dict(zip(fields, shape_record.record))
            features.append(
                {
                    "type": "Feature",
                    "geometry": geometry,
                    "properties": properties,
                }
            )

        return {
            "type": "FeatureCollection",
            "features": features,
        }
    except Exception as exc:
        raise ValueError(f"Ошибка преобразования Shapefile в GeoJSON: {exc}") from exc
    finally:
        reader.close()


def find_shp_file(work_dir: Path) -> Path:
    """Находит первый .shp-файл во временной папке."""
    shp_files = sorted(work_dir.rglob("*.shp"))
    if not shp_files:
        raise ValueError("Ошибка: файл .shp не найден.")
    return shp_files[0]


def extract_zip(zip_path: Path, work_dir: Path) -> None:
    """Распаковывает ZIP-архив во временную папку."""
    try:
        with zipfile.ZipFile(zip_path, "r") as archive:
            archive.extractall(work_dir)
    except zipfile.BadZipFile as exc:
        raise ValueError("Ошибка: ZIP-архив поврежден или имеет неверный формат.") from exc


async def save_upload(file: UploadFile, target_dir: Path) -> Path:
    """Сохраняет загруженный файл во временную папку."""
    filename = safe_filename(file.filename or "upload")
    target_path = target_dir / filename

    with target_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    await file.close()
    return target_path


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Главная страница приложения."""
    return templates.TemplateResponse("index.html", {"request": request, "result": None})


@app.head("/")
async def index_head() -> None:
    """Проверка доступности главной страницы для Render и HTTP-клиентов."""
    return None


@app.post("/upload", response_class=HTMLResponse)
async def upload(request: Request, files: list[UploadFile] = File(...)) -> HTMLResponse:
    """
    Endpoint загрузки данных.

    Можно отправить один ZIP-архив или сразу набор файлов Shapefile:
    .shp, .shx, .dbf, .prj, .cpg.
    """
    work_dir = TEMP_DIR / str(uuid.uuid4())
    work_dir.mkdir(parents=True, exist_ok=True)

    try:
        if not files:
            raise ValueError("Ошибка: файлы не были выбраны.")

        uploaded_names = [safe_filename(file.filename or "upload") for file in files]
        saved_paths = [await save_upload(file, work_dir) for file in files]

        zip_files = [path for path in saved_paths if path.suffix.lower() == ".zip"]

        if zip_files and len(saved_paths) > 1:
            raise ValueError("Ошибка: загрузите либо один ZIP-архив, либо набор файлов Shapefile без ZIP.")

        if zip_files:
            extract_zip(zip_files[0], work_dir)
            display_name = zip_files[0].name
        else:
            invalid_files = [
                path.name for path in saved_paths if path.suffix.lower() not in ALLOWED_DIRECT_EXTENSIONS
            ]
            if invalid_files:
                raise ValueError(
                    "Ошибка: для прямой загрузки разрешены только файлы .shp, .shx, .dbf, .prj, .cpg."
                )
            display_name = ", ".join(uploaded_names)

        shp_path = find_shp_file(work_dir)
        geojson = read_shapefile(shp_path)
        features = geojson["features"]

        result = make_result(
            filename=display_name,
            status="Данные успешно загружены и обработаны",
            objects_count=len(features),
            features=features[:2],
        )
    except ValueError as exc:
        result = make_result(
            filename=", ".join(safe_filename(file.filename or "upload") for file in files),
            status="Данные не обработаны",
            error=str(exc),
        )
    except Exception as exc:
        result = make_result(
            filename=", ".join(safe_filename(file.filename or "upload") for file in files),
            status="Данные не обработаны",
            error=f"Непредвиденная ошибка обработки: {exc}",
        )
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)

    return templates.TemplateResponse("index.html", {"request": request, "result": result})
