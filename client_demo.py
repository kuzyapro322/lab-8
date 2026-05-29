# Импорты
# argparse — для запуска демонстрации с другим адресом сервера при необходимости
# json — для красивого вывода JSON-ответов API
# requests — для раздела I: отправки HTTP-запросов к Flask API из отдельного клиента

import argparse
import json

import requests


# ==============================
# Раздел II — Демонстрационный клиент для проверки API
# ==============================

def print_response(title, response):
    print(f"\n{title}")
    print(f"HTTP {response.status_code}")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=4))
    except ValueError:
        print(response.text)


def main():
    parser = argparse.ArgumentParser(description="Проверка key-value API лабораторной работы №8.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Адрес Flask-приложения.")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    print_response(
        "1. POST /set — сохраняем ключ.",
        requests.post(
            f"{base_url}/set",
            json={"key": "demo_client", "value": "Значение отправлено через requests"},
            timeout=5,
        ),
    )
    print_response("2. GET /get/demo_client — получаем значение.", requests.get(f"{base_url}/get/demo_client", timeout=5))
    print_response("3. GET /exists/demo_client — проверяем наличие.", requests.get(f"{base_url}/exists/demo_client", timeout=5))
    print_response("4. DELETE /delete/demo_client — удаляем ключ.", requests.delete(f"{base_url}/delete/demo_client", timeout=5))
    print_response("5. GET /exists/demo_client — убеждаемся, что ключ удален.", requests.get(f"{base_url}/exists/demo_client", timeout=5))


if __name__ == "__main__":
    main()
