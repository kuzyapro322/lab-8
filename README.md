# Лабораторная работа №8

Тема: разработка key-value хранилища на Flask.

## Что реализовано

- словарь `data` как основное key-value хранилище;
- автоматическая загрузка данных из `data.json` при старте приложения;
- сохранение изменений в `data.json` после каждой операции `/set` и `/delete/<key>`;
- API-маршруты `POST /set`, `GET /get/<key>`, `DELETE /delete/<key>`, `GET /exists/<key>`;
- общее ограничение `100 per day` для маршрутов;
- отдельное ограничение `10 per minute` для `/set` и `/delete/<key>`;
- HTML-страница `/` для наглядной проверки API;
- демонстрационный клиент `client_demo.py` на библиотеке `requests`.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

После запуска приложение доступно по адресу:

```text
http://127.0.0.1:5000
```

## API

Сохранить значение:

```bash
curl -i -X POST http://127.0.0.1:5000/set ^
  -H "Content-Type: application/json" ^
  -d "{\"key\":\"student\",\"value\":\"ФБИ\"}"
```

Получить значение:

```bash
curl -i http://127.0.0.1:5000/get/student
```

Проверить наличие ключа:

```bash
curl -i http://127.0.0.1:5000/exists/student
```

Удалить ключ:

```bash
curl -i -X DELETE http://127.0.0.1:5000/delete/student
```

## Проверка через requests

```bash
python client_demo.py
```

Скрипт последовательно выполняет сохранение, получение, проверку существования, удаление и повторную проверку ключа.
