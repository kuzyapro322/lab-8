# Импорты
# json — для раздела II: загрузки и сохранения key-value данных в файле data.json
# os — для общей части: чтения переменных окружения DATA_FILE и FLASK_PORT
# pathlib.Path — для общей части: безопасной работы с путями к файлам проекта
# threading.RLock — для раздела II: защиты словаря data и файла data.json от одновременной записи
# typing.Any — для раздела II: описания значений, которые могут храниться в key-value хранилище
# flask — для раздела II: создания API-маршрутов, HTML-страницы и JSON-ответов
# flask_limiter — для раздела II: ограничения частоты запросов к API
# werkzeug.exceptions.HTTPException — для общей части: аккуратной обработки HTTP-ошибок

import json
import os
from pathlib import Path
from threading import RLock
from typing import Any

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.errors import RateLimitExceeded
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException


# ==============================
# Раздел II — Настройка приложения и файла хранения
# ==============================

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = Path(os.getenv("DATA_FILE", BASE_DIR / "data.json")).resolve()

app = Flask(__name__)

# limiter ограничивает все маршруты общим правилом 100 запросов в сутки.
# Для POST /set и DELETE /delete/<key> ниже добавлены отдельные лимиты 10 запросов в минуту.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per day"],
    storage_uri="memory://",
)

# data — основное key-value хранилище лабораторной работы.
# Ключ всегда строковый, значение может быть строкой, числом, списком, объектом JSON и т.д.
data: dict[str, Any] = {}
data_lock = RLock()


# ==============================
# Раздел II — Загрузка и сохранение данных
# ==============================

def save_data() -> None:
    # После каждой изменяющей операции записываем актуальное состояние словаря data в data.json.
    with data_lock:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        temp_file = DATA_FILE.with_suffix(DATA_FILE.suffix + ".tmp")
        temp_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True),
            encoding="utf-8",
        )
        temp_file.replace(DATA_FILE)


def load_data() -> None:
    # При старте приложения автоматически загружаем data.json в словарь data.
    with data_lock:
        if not DATA_FILE.exists():
            save_data()
            return

        loaded_data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(loaded_data, dict):
            raise RuntimeError("Файл data.json должен содержать JSON-объект с парами ключ-значение.")

        data.clear()
        data.update(loaded_data)


def current_snapshot() -> dict[str, Any]:
    # Отдаем копию словаря, чтобы шаблон или API-ответ не меняли основное хранилище напрямую.
    with data_lock:
        return dict(data)


# ==============================
# Раздел II — Проверка входных данных API
# ==============================

def request_payload() -> dict[str, Any]:
    # API принимает JSON-запросы, а демонстрационная HTML-страница отправляет обычную form-data форму.
    payload = request.get_json(silent=True) if request.is_json else None
    if payload is None:
        payload = request.form.to_dict()

    if not isinstance(payload, dict):
        raise ValueError("Тело запроса должно быть JSON-объектом или HTML-формой.")
    return payload


def normalize_key(raw_key: Any) -> str:
    # Ключ приводится к строке и обрезается по краям, чтобы ' user ' и 'user' не считались разными ключами.
    key = str(raw_key or "").strip()
    if not key:
        raise ValueError("Ключ обязателен.")
    if len(key) > 100:
        raise ValueError("Ключ не должен быть длиннее 100 символов.")
    return key


def validate_value(value: Any) -> Any:
    # Значение должно сериализоваться в JSON, иначе его невозможно надежно сохранить в data.json.
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError as error:
        raise ValueError("Значение должно быть JSON-сериализуемым.") from error
    return value


def error_response(message: str, status_code: int):
    # Единый формат ошибок помогает одинаково читать ответы в браузере, curl и Postman.
    response = jsonify({
        "ok": False,
        "message": message,
    })
    return response, status_code


# ==============================
# Раздел II — HTML-страница для наглядной проверки API
# ==============================

@app.get("/")
def index():
    # Страница не заменяет API, а только показывает преподавателю текущее состояние и дает удобные формы проверки.
    return render_template(
        "index.html",
        items=current_snapshot(),
        data_file=str(DATA_FILE),
        default_limit="100 запросов в сутки",
        write_limit="10 запросов в минуту для /set и /delete",
    )


# ==============================
# Раздел II — API: просмотр всех данных для демонстрационной страницы
# ==============================

@app.get("/all")
def all_items():
    # Вспомогательный маршрут нужен для обновления таблицы на HTML-странице после API-операций.
    return jsonify({
        "ok": True,
        "count": len(data),
        "data": current_snapshot(),
    })


# ==============================
# Раздел II — API: POST /set — сохранить ключ-значение
# ==============================

@app.post("/set")
@limiter.limit("10 per minute", override_defaults=False)
def set_value():
    try:
        payload = request_payload()
        key = normalize_key(payload.get("key"))
        if "value" not in payload:
            raise ValueError("Значение обязательно.")

        value = validate_value(payload["value"])
        with data_lock:
            data[key] = value
            save_data()

        return jsonify({
            "ok": True,
            "message": "Значение сохранено.",
            "key": key,
            "value": value,
            "count": len(data),
        }), 201
    except ValueError as error:
        return error_response(str(error), 400)


# ==============================
# Раздел II — API: GET /get/<key> — получить значение по ключу
# ==============================

@app.get("/get/")
def get_value_without_key():
    return error_response("Передайте ключ в адресе: /get/<key>.", 400)


@app.get("/get/<path:key>")
def get_value(key: str):
    key = normalize_key(key)
    with data_lock:
        if key not in data:
            return error_response("Ключ не найден.", 404)
        value = data[key]

    return jsonify({
        "ok": True,
        "key": key,
        "value": value,
    })


# ==============================
# Раздел II — API: DELETE /delete/<key> — удалить ключ
# ==============================

@app.delete("/delete/")
def delete_value_without_key():
    return error_response("Передайте ключ в адресе: /delete/<key>.", 400)


@app.delete("/delete/<path:key>")
@limiter.limit("10 per minute", override_defaults=False)
def delete_value(key: str):
    key = normalize_key(key)
    with data_lock:
        if key not in data:
            return error_response("Ключ не найден.", 404)
        removed_value = data.pop(key)
        save_data()

    return jsonify({
        "ok": True,
        "message": "Ключ удален.",
        "key": key,
        "removed_value": removed_value,
        "count": len(data),
    })


# ==============================
# Раздел II — API: GET /exists/<key> — проверить наличие ключа
# ==============================

@app.get("/exists/")
def exists_without_key():
    return error_response("Передайте ключ в адресе: /exists/<key>.", 400)


@app.get("/exists/<path:key>")
def exists(key: str):
    key = normalize_key(key)
    with data_lock:
        key_exists = key in data

    return jsonify({
        "ok": True,
        "key": key,
        "exists": key_exists,
    })


# ==============================
# Общая часть — Обработка ошибок
# ==============================

@app.errorhandler(RateLimitExceeded)
def handle_rate_limit(error: RateLimitExceeded):
    return error_response(f"Превышен лимит запросов: {error.description}.", 429)


@app.errorhandler(HTTPException)
def handle_http_error(error: HTTPException):
    return error_response(error.description, error.code or 500)


# ==============================
# Общая часть — Запуск приложения
# ==============================

load_data()

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug_mode = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
