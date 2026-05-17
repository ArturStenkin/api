import json
from html import escape
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

import shapefile
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse


# Пути проекта. Папка temp используется только для временной обработки загрузок.
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Spatial Data API",
    description="WebAPI для загрузки ZIP-архивов и файлов Shapefile",
    version="1.0.0",
)

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


def render_page(result: dict[str, Any] | None = None) -> HTMLResponse:
    """Формирует HTML-страницу без внешних шаблонов, чтобы деплой был надежнее."""
    result_block = ""

    if result:
        if result["error"]:
            result_block = f"""
            <hr class="my-4">
            <div class="alert alert-danger mb-0" role="alert">
              <h2 class="h5 alert-heading">Ошибка обработки</h2>
              <p class="mb-1"><strong>Имя файла:</strong> {escape(result["filename"])}</p>
              <p class="mb-1"><strong>Статус:</strong> {escape(result["status"])}</p>
              <p class="mb-0">{escape(result["error"])}</p>
            </div>
            """
        else:
            result_block = f"""
            <hr class="my-4">
            <div class="result-grid">
              <div class="result-item">
                <span>Имя файла</span>
                <strong>{escape(result["filename"])}</strong>
              </div>
              <div class="result-item">
                <span>Статус</span>
                <strong>{escape(result["status"])}</strong>
              </div>
              <div class="result-item">
                <span>Количество объектов</span>
                <strong>{result["objects_count"]}</strong>
              </div>
            </div>
            <h2 class="json-title">Первые 2 объекта GeoJSON</h2>
            <pre class="json-output"><code>{escape(result["features_json"])}</code></pre>
            """

    html = f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Система загрузки пространственных данных</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
      body {{
        min-height: 100vh;
        margin: 0;
        background: linear-gradient(135deg, #f7fbff 0%, #edf4f8 54%, #ffffff 100%);
        color: #1f2937;
      }}

      .page-shell {{
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 32px 16px;
      }}

      .app-card {{
        width: min(100%, 960px);
        overflow: hidden;
        border-radius: 18px;
        background: #ffffff;
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.13);
      }}

      .hero {{
        padding: 34px;
        border-bottom: 1px solid #e5e7eb;
      }}

      .hero h1 {{
        max-width: 760px;
        margin: 0 0 14px;
        font-size: 2rem;
        font-weight: 750;
        letter-spacing: 0;
      }}

      .hero p {{
        max-width: 780px;
        margin: 0;
        color: #5b6472;
        font-size: 1.05rem;
        line-height: 1.6;
      }}

      .content {{
        padding: 34px;
      }}

      .upload-form {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 18px;
        align-items: end;
      }}

      .api-link {{
        margin-top: 16px;
      }}

      .result-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }}

      .result-item {{
        min-height: 96px;
        padding: 18px;
        border: 1px solid #dbe4ee;
        border-radius: 12px;
        background: #f8fbff;
      }}

      .result-item span {{
        display: block;
        margin-bottom: 8px;
        color: #6b7280;
        font-size: 0.92rem;
      }}

      .result-item strong {{
        display: block;
        overflow-wrap: anywhere;
        color: #1f2937;
      }}

      .json-title {{
        margin: 28px 0 14px;
        font-size: 1.15rem;
        font-weight: 700;
      }}

      .json-output {{
        max-height: 440px;
        margin: 0;
        overflow: auto;
        border-radius: 14px;
        background: #111827;
        color: #e5e7eb;
        padding: 20px;
        font-size: 0.92rem;
        line-height: 1.55;
        white-space: pre-wrap;
      }}

      @media (max-width: 760px) {{
        .hero,
        .content {{
          padding: 24px;
        }}

        .hero h1 {{
          font-size: 1.55rem;
        }}

        .upload-form,
        .result-grid {{
          grid-template-columns: 1fr;
        }}
      }}
    </style>
  </head>
  <body>
    <main class="page-shell">
      <section class="app-card">
        <div class="hero">
          <span class="badge rounded-pill text-bg-primary-subtle text-primary-emphasis mb-3">FastAPI + pyshp</span>
          <h1>Система загрузки пространственных данных</h1>
          <p>
            Загрузите ZIP-архив с Shapefile или выберите отдельные файлы
            .shp, .shx, .dbf, .prj, .cpg. Приложение прочитает данные и
            покажет результат в формате GeoJSON.
          </p>
        </div>

        <div class="content">
          <form action="/upload" method="post" enctype="multipart/form-data" class="upload-form">
            <div>
              <label for="files" class="form-label fw-semibold">Файлы пространственных данных</label>
              <input
                class="form-control form-control-lg"
                type="file"
                id="files"
                name="files"
                accept=".zip,.shp,.shx,.dbf,.prj,.cpg"
                multiple
                required
              >
              <div class="form-text">
                Можно выбрать один ZIP или сразу несколько файлов Shapefile.
              </div>
            </div>
            <button class="btn btn-primary btn-lg" type="submit">Загрузить и обработать</button>
          </form>

          <div class="api-link">
            <a href="/docs" class="link-primary">Открыть Swagger UI</a>
          </div>

          {result_block}
        </div>
      </section>
    </main>
  </body>
</html>"""

    return HTMLResponse(content=html)


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


def get_encoding_candidates(shp_path: Path) -> list[str]:
    """Возвращает список кодировок для чтения DBF-таблицы."""
    candidates = []
    cpg_path = shp_path.with_suffix(".cpg")

    if cpg_path.exists():
        cpg_encoding = cpg_path.read_text(encoding="utf-8", errors="ignore").strip()
        if cpg_encoding:
            candidates.append(cpg_encoding)

    candidates.extend(["utf-8", "cp1251", "latin1"])

    unique_candidates = []
    for encoding in candidates:
        normalized = encoding.lower()
        if normalized not in [item.lower() for item in unique_candidates]:
            unique_candidates.append(encoding)

    return unique_candidates


def read_shapefile_with_encoding(shp_path: Path, encoding: str) -> dict[str, Any]:
    """Читает Shapefile в заданной кодировке DBF-таблицы."""
    try:
        reader = shapefile.Reader(str(shp_path), encoding=encoding)
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


def read_shapefile(shp_path: Path) -> dict[str, Any]:
    """Читает Shapefile через pyshp и возвращает GeoJSON FeatureCollection."""
    last_error: Exception | None = None

    for encoding in get_encoding_candidates(shp_path):
        try:
            return read_shapefile_with_encoding(shp_path, encoding)
        except (UnicodeDecodeError, ValueError) as exc:
            last_error = exc

    raise ValueError(f"Ошибка чтения Shapefile: не удалось подобрать кодировку DBF. {last_error}")


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
async def index() -> HTMLResponse:
    """Главная страница приложения."""
    return render_page()


@app.head("/")
async def index_head() -> None:
    """Проверка доступности главной страницы для Render и HTTP-клиентов."""
    return None


@app.post("/upload", response_class=HTMLResponse)
async def upload(files: list[UploadFile] = File(...)) -> HTMLResponse:
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

    return render_page(result)
