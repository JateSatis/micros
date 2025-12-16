# Микросервисная система бронирования отелей

Система состоит из 8 микросервисов, реализованных на FastAPI с PostgreSQL.

## Структура проекта

- `auth/` - Микросервис авторизации (порт 8001)
- `profile/` - Микросервис профиля (порт 8002)
- `jobs/` - Микросервис каталога вакансий (порт 8003)
- `applications/` - Микросервис откликов (порт 8004)
- `reviews/` - Микросервис отзывов (порт 8005)
- `mailing/` - Микросервис рассылки (порт 8006)
- `verification/` - Микросервис верификации (порт 8007)
- `notifications/` - Микросервис уведомлений (порт 8008)

## Требования

- Docker
- Docker Compose

## Запуск системы

### 1. Запуск всех сервисов

```bash
docker-compose up --build
```

Эта команда:

- Создаст 8 контейнеров PostgreSQL (по одному для каждого микросервиса)
- Соберет и запустит все 8 микросервисов
- Настроит сеть между сервисами

### 2. Запуск в фоновом режиме

```bash
docker-compose up -d --build
```

### 3. Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f auth-service
docker-compose logs -f profile-service
```

### 4. Остановка системы

```bash
docker-compose down
```

### 5. Остановка с удалением данных

```bash
docker-compose down -v
```

## Проверка работоспособности

После запуска все сервисы будут доступны по следующим адресам:

- Auth Service: http://localhost:8001
- Profile Service: http://localhost:8002
- Jobs Service: http://localhost:8003
- Applications Service: http://localhost:8004
- Reviews Service: http://localhost:8005
- Mailing Service: http://localhost:8006
- Verification Service: http://localhost:8007
- Notifications Service: http://localhost:8008

### Проверка health endpoints

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
curl http://localhost:8006/health
curl http://localhost:8007/health
curl http://localhost:8008/health
```

## Примеры использования API

### 1. Регистрация пользователя

```bash
curl -X POST http://localhost:8001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "strongPassword123",
    "full_name": "Иван Иванов",
    "role": "candidate"
  }'
```

### 2. Вход в систему

```bash
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "strongPassword123"
  }'
```

Ответ содержит `access_token`, который нужно использовать для авторизованных запросов.

### 3. Создание резюме (требует авторизации)

```bash
curl -X POST http://localhost:8002/api/profile/resumes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "Frontend Developer",
    "position": "React-разработчик",
    "skills": ["React", "TypeScript", "Redux"],
    "experience": [{
      "company": "TechCorp",
      "position": "Frontend Developer",
      "start_date": "2022-03-01",
      "end_date": "2024-06-01",
      "description": "Разработка SPA-приложений"
    }],
    "education": [{
      "institution": "МГУ",
      "degree": "Бакалавр",
      "year": 2021
    }],
    "description": "Опытный фронтенд-разработчик с фокусом на UX."
  }'
```

### 4. Создание вакансии (требует авторизации и роль employer)

```bash
curl -X PUT http://localhost:8003/api/jobs \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "title": "Backend-разработчик (Golang)",
    "description": "Разработка микросервисов для платформы hh-аналога",
    "requirements": ["Golang", "PostgreSQL", "Docker", "REST API"],
    "salary": 250000,
    "currency": "RUB",
    "location": "Москва",
    "employment_type": "full_time"
  }'
```

### 5. Поиск вакансий (без авторизации)

```bash
curl "http://localhost:8003/api/jobs/search?query=backend&location=Москва&salary_from=150000&page=1&limit=10"
```

## Документация API

После запуска сервисов, интерактивная документация Swagger доступна по адресам:

- http://localhost:8001/docs
- http://localhost:8002/docs
- http://localhost:8003/docs
- http://localhost:8004/docs
- http://localhost:8005/docs
- http://localhost:8006/docs
- http://localhost:8007/docs
- http://localhost:8008/docs

## Устранение проблем

### Проблема: Сервисы не запускаются

1. Проверьте, что порты 8001-8008 и 5432-5439 свободны
2. Проверьте логи: `docker-compose logs`
3. Убедитесь, что Docker запущен

### Проблема: Ошибки подключения к БД

1. Дождитесь полной инициализации PostgreSQL (может занять 10-30 секунд)
2. Проверьте healthcheck: `docker-compose ps`
3. Перезапустите сервисы: `docker-compose restart`

### Проблема: Ошибки авторизации

1. Убедитесь, что используете правильный токен из `/api/auth/login`
2. Проверьте, что токен не истек (время жизни: 1 час)
3. Убедитесь, что заголовок `Authorization: Bearer TOKEN` правильно установлен

## Примечания

- Все пароли хешируются с помощью bcrypt
- JWT токены имеют время жизни 1 час
- Базы данных используют volumes для сохранения данных между перезапусками
- Для продакшена рекомендуется изменить секретные ключи в docker-compose.yml
