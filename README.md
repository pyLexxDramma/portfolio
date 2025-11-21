# Unified Parser - Парсер для Yandex.Maps и 2GIS

Парсер для одновременного сбора данных с Yandex.Maps и 2GIS с веб-интерфейсом и генерацией отчетов.

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Скопируйте `.env.example` в `.env` и заполните своими данными:
```bash
cp .env.example .env
```

3. Отредактируйте `.env` файл:
   - Установите `SITE_PASSWORD` для защиты веб-интерфейса
   - Настройте прокси (если требуется): `PROXY_ENABLED=true`, `PROXY_SERVER`, `PROXY_PORT`, `PROXY_USERNAME`, `PROXY_PASSWORD`
   - Настройте SMTP для email уведомлений (если требуется)

4. Запустите сервер:
```bash
python run_server.py
```

5. Откройте браузер и перейдите на `http://localhost:8000`

## Конфигурация

### Файл `.env`

Создайте файл `.env` в корне проекта на основе `.env.example`. Файл `.env` уже создан с вашими данными.

**Настройка SMTP для email уведомлений:**

#### Для Gmail:
```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password  # Используйте App Password, не обычный пароль!
```
⚠️ **Важно для Gmail**: Нужно использовать [App Password](https://support.google.com/accounts/answer/185833), а не обычный пароль. Включите 2FA и создайте App Password в настройках Google Account.

#### Для Yandex:
```env
SMTP_SERVER=smtp.yandex.ru
SMTP_PORT=465
SMTP_USER=your_email@yandex.ru
SMTP_PASSWORD=your_password
```

#### Для Mail.ru:
```env
SMTP_SERVER=smtp.mail.ru
SMTP_PORT=465
SMTP_USER=your_email@mail.ru
SMTP_PASSWORD=your_password
```

**Примечание**: После настройки SMTP раскомментируйте соответствующие строки в `.env` файле.

### Файл `config/config.json`

Дополнительные настройки парсера (лимиты, таймауты и т.д.) можно настроить в `config/config.json`.

## Использование

1. Войдите в систему с паролем из `.env` (или `config.json`)
2. Заполните форму:
   - Название компании
   - Сайт компании
   - Выберите источник (Yandex, 2GIS или оба)
   - Email для уведомлений
   - Область поиска (город или страна)
3. Нажмите "Начать парсинг"
4. Следите за прогрессом на странице статуса задачи
5. После завершения скачайте PDF отчет

## Особенности

- ✅ Одновременный парсинг Yandex.Maps и 2GIS
- ✅ Прогресс-бар с этапами парсинга в реальном времени
- ✅ Генерация PDF отчетов
- ✅ Защита паролем
- ✅ Поддержка прокси с аутентификацией
- ✅ Email уведомления (опционально)
- ✅ Детальная статистика по карточкам и отзывам

## Структура проекта

```
unified_parser_v2/
├── config/
│   └── config.json          # Основные настройки
├── src/
│   ├── config/
│   │   └── settings.py      # Загрузка настроек из .env и config.json
│   ├── drivers/
│   │   └── selenium_driver.py
│   ├── parsers/
│   │   ├── yandex_parser.py
│   │   └── gis_parser.py
│   ├── storage/
│   │   ├── csv_writer.py
│   │   └── pdf_writer.py
│   ├── webapp/
│   │   ├── app.py
│   │   ├── templates/
│   │   └── static/
│   └── utils/
│       └── task_manager.py
├── .env                      # Ваши секретные данные (не в git)
├── .env.example              # Пример файла .env
├── run_server.py
└── requirements.txt
```

## Безопасность

⚠️ **Важно**: Файл `.env` содержит секретные данные и не должен попадать в git. Он уже добавлен в `.gitignore`.
