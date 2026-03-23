# Roma Coffee

Django-проект для кофейни с:
- регистрацией и входом по номеру телефона
- JWT-авторизацией
- личным кабинетом пользователя
- ролями `customer` и `barista`
- персональным QR-кодом пользователя
- акцией `6+1`: после 6 оплаченных кофе следующий бесплатный
- кабинетом баристы со сканированием QR-кода

## Что реализовано

### Аутентификация
- Кастомная модель пользователя `users.User`
- Логин по полю `phone`
- Пароль хранится стандартными Django hasher'ами
- JWT:
  - короткий `access token`
  - длинный `refresh token`
- Refresh-сессии хранятся в БД
- HTML-формы:
  - вход
  - регистрация
  - восстановление пароля

### Роли
- `customer` — обычный пользователь
- `barista` — бариста

Роль хранится в модели пользователя и редактируется через Django admin.

### Личный кабинет пользователя
- отображение телефона
- отображение роли
- отображение прогресса по акции
- отображение статуса акции
- генерация и перевыпуск персонального QR-кода
- автоматическое обновление счетчика кофе после сканирования баристой

### Кабинет баристы
- отдельная страница для баристы
- ручной ввод UUID из QR
- сканирование QR-кода камерой телефона
- начисление кофе пользователю
- отображение результата сканирования
- кнопка возврата в обычный кабинет

### Акция 6+1
Логика:
- пользователь копит 6 оплаченных кофе
- на 6-й отметке получает сообщение: `Следующий кофе бесплатно!`
- на следующем скане:
  - бариста видит сообщение: `Сделать бесплатный кофе!`
  - пользователь видит сообщение: `Спасибо что вы выпили первые 6 у нас!!!`
  - счетчик сбрасывается на `0/6`

## Технологии
- Python 3.11+
- Django
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Docker Compose
- `qrcode[pil]`

## Структура

Основная логика лежит в:
- [config/settings.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/config/settings.py)
- [users/models.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/users/models.py)
- [users/views.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/users/views.py)
- [users/services.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/users/services.py)
- [users/presenters.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/users/presenters.py)
- [users/domain/loyalty.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/users/domain/loyalty.py)
- [users/domain/roles.py](/D:/web_develop/roma_coffee/docs/code/roma_coffee/users/domain/roles.py)
- [templates/auth/dashboard.html](/D:/web_develop/roma_coffee/docs/code/roma_coffee/templates/auth/dashboard.html)
- [templates/auth/barista_dashboard.html](/D:/web_develop/roma_coffee/docs/code/roma_coffee/templates/auth/barista_dashboard.html)

## Зависимости

Сейчас в проекте используются:

```toml
django>=5.2.12
djangorestframework>=3.16.1
djangorestframework-simplejwt>=5.5.1
psycopg[binary]>=3.2.9
python-dotenv>=1.1.1
qrcode[pil]>=8.2
```

## Переменные окружения

Пример `.env`:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=

POSTGRES_DB=roma_coffee
POSTGRES_USER=roma_user
POSTGRES_PASSWORD=roma_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432

AUTH_COOKIE_SECURE=False
AUTH_COOKIE_SAMESITE=Lax
```

Примечания:
- `DJANGO_ALLOWED_HOSTS` — без `http://` и `https://`
- `DJANGO_CSRF_TRUSTED_ORIGINS` — с `https://`

## Локальный запуск

### 1. Поднять PostgreSQL

```powershell
docker compose up -d
```

### 2. Установить зависимости

Если используете `uv`:

```powershell
uv sync
```

### 3. Применить миграции

```powershell
python manage.py migrate
```

### 4. Создать суперпользователя

```powershell
python manage.py createsuperuser
```

### 5. Запустить сервер

```powershell
python manage.py runserver 0.0.0.0:8000
```

## Админка

Админка доступна по:

```text
/admin/
```

В `UserAdmin` доступны для редактирования все текущие поля пользователя:
- `phone`
- `role`
- `coffee_count`
- `free_coffee_available`
- `loyalty_status`
- `qr_code_uuid`
- `qr_code_updated_at`
- `is_active`
- `is_staff`
- `is_superuser`
- `groups`
- `user_permissions`

Через админку можно:
- назначать баристу
- вручную менять счетчик кофе
- сбрасывать или включать бесплатный кофе
- менять статус акции
- менять UUID QR-кода

## Основные URL

### HTML
- `/auth/login/`
- `/auth/register/`
- `/auth/password-reset/`
- `/auth/dashboard/`
- `/auth/barista/`

### API
- `/auth/api/register/`
- `/auth/api/login/`
- `/auth/api/refresh/`
- `/auth/api/logout/`
- `/auth/api/me/`
- `/auth/api/password-reset/`
- `/auth/api/password-reset/confirm/`
- `/auth/dashboard/state/`

## Как работает QR

### Для пользователя
- в кабинете можно создать или обновить QR-код
- QR содержит UUID пользователя
- UUID сохраняется в поле `qr_code_uuid`

### Для баристы
- бариста открывает `/auth/barista/`
- сканирует QR камерой или вставляет UUID вручную
- сервер находит пользователя по `qr_code_uuid`
- пользователю начисляется кофе по правилам акции

## Автообновление кабинета пользователя

После сканирования баристой пользовательский кабинет обновляется автоматически:
- страница пользователя опрашивает `/auth/dashboard/state/`
- обновляются:
  - счетчик кофе
  - статус акции
  - связанные карточки кабинета

Это сделано без WebSocket, через периодический polling.

## Запуск на телефоне через ngrok

Если нужно открыть проект на телефоне и использовать камеру браузера, нужен `https`.

### 1. Установить ngrok

На Windows:

```powershell
winget install ngrok.ngrok или в Win store
```

### 2. Получить токен

Зарегистрируйтесь в ngrok и возьмите токен:

```text
https://dashboard.ngrok.com/get-started/your-authtoken
```

### 3. Привязать токен

```powershell
ngrok config add-authtoken YOUR_TOKEN
```

### 4. Запустить Django

```powershell
python manage.py runserver 0.0.0.0:8000
```

### 5. Запустить туннель

```powershell
ngrok http 8000
```

### 6. Добавить адрес ngrok в `.env`

Пример:

```env
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost,6f7d-103-104-246-149.ngrok-free.app
DJANGO_CSRF_TRUSTED_ORIGINS=https://6f7d-103-104-246-149.ngrok-free.app
AUTH_COOKIE_SECURE=False
```

Важно:
- `DJANGO_ALLOWED_HOSTS` без `https://`
- `DJANGO_CSRF_TRUSTED_ORIGINS` с `https://`
- при каждом новом адресе `ngrok` эти значения надо обновлять

### 7. Перезапустить Django

После изменения `.env` обязательно перезапустите сервер:

```powershell
python manage.py runserver 0.0.0.0:8000
```

### 8. Открыть на телефоне

Открывайте именно:

```text
https://...ngrok-free.app
```

Не `http://...`, а `https://`.

## Почему камера может не работать на телефоне

Проверьте:
- сайт открыт по `https`
- браузеру выдан доступ к камере
- открываете не во встроенном браузере мессенджера
- лучше использовать Chrome / Edge / Safari
- на телефоне есть интернет, если сканер грузит библиотеку с CDN

Если страница открыта по обычному `http://192.168...`, мобильный браузер обычно блокирует камеру.

## Что уже исправлялось по ходу работы
- повторное начисление кофе при refresh у баристы
- CSRF при работе через `ngrok`
- `DisallowedHost` для `ngrok`
- безопасный формат Django-шаблонов без разрыва `%}`
- автообновление кабинета пользователя после скана

## Возможные следующие улучшения
- хранить JS-библиотеку QR локально, а не через CDN
- WebSocket/SSE вместо polling
- история сканов баристы
- защита от двойного сканирования одного и того же QR подряд
- отдельная таблица операций лояльности
- более строгая production-настройка cookies и HTTPS
